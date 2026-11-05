import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langex/app/providers.dart';
import 'package:langex/app/router.dart';
import 'package:langex/core/auth/session.dart';

import '../support/fakes.dart';

const _contribution = {
  'id': 'c1',
  'pair_id': pairId,
  'author_id': partner,
  'learner_id': me,
  'language': 'ar',
  'text': 'صباح الخير',
  'created_at': '2026-11-05T08:00:00Z',
  'gloss': 'Dobro jutro',
  'gloss_language': 'bs',
  'note': 'Morning greeting',
};

const _attempt = {
  'id': 'a1',
  'pair_id': pairId,
  'learner_id': partner,
  'reviewer_id': me,
  'language': 'bs',
  'text': 'Ja sam dobro',
  'created_at': '2026-11-05T09:00:00Z',
  'correction': null,
};

void main() {
  test('route guard', () {
    expect(guard(SessionStatus.loading, '/'), '/splash');
    expect(guard(SessionStatus.signedOut, '/pairs/x'), '/sign-in');
    expect(guard(SessionStatus.signedOut, '/sign-in'), isNull);
    expect(guard(SessionStatus.signedIn, '/sign-in'), '/');
    expect(guard(SessionStatus.signedIn, '/review'), isNull);
  });

  testWidgets('signs in with the development provider', (tester) async {
    final api = FakeBackend()
      ..on('POST', '/v1/auth/sign-in', {
        'access_token': 'a',
        'refresh_token': 'r',
        'token_type': 'bearer',
        'expires_in': 900,
        'account_id': me,
        'is_new_account': true,
      })
      ..on('GET', '/v1/pairs', <Object>[])
      ..on('GET', '/v1/languages', <Object>[]);
    final container = await pumpApp(tester, api);

    expect(
      find.text('Learn a language with a friend who speaks it'),
      findsOneWidget,
    );
    await tester.tapAndSettle(find.text('Sign in'));
    expect(find.text('Required'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('dev-name')), '  amina ');
    await tester.tapAndSettle(find.text('Sign in'));

    expect(api.bodyOf('POST /v1/auth/sign-in'), {
      'provider': 'dev',
      'id_token': 'dev:amina',
    });
    expect(container.read(sessionProvider).status, SessionStatus.signedIn);
    expect(find.text('Start with a partner'), findsOneWidget);
  });

  testWidgets('without dev sign-in the button is not offered', (tester) async {
    await pumpApp(tester, FakeBackend(), devSignIn: false);
    expect(find.byKey(const Key('dev-name')), findsNothing);
    expect(
      find.text("Sign-in isn't available in this build yet."),
      findsOneWidget,
    );
  });

  testWidgets('home shows the pair, streak and work for today', (tester) async {
    final api = FakeBackend();
    seedPair(api, streak: 3);
    api
      ..on('GET', '/v1/attempts/to-review', [_attempt])
      ..on('GET', '/v1/reviews/session', [
        {
          'id': 'k1',
          'item_id': 'c1',
          'due': '2026-11-05T00:00:00Z',
          'phase': 'learning',
          'is_new': true,
        },
      ]);
    await pumpApp(tester, api, tokens: signedIn());

    expect(find.text('You teach bosanski · you learn العربية'), findsOneWidget);
    expect(find.text('3-day streak'), findsOneWidget);
    expect(find.text('1 card to review'), findsOneWidget);
    expect(find.text('1 sentence to correct'), findsOneWidget);
  });

  testWidgets('a session that cannot be refreshed returns to sign-in', (
    tester,
  ) async {
    final api = FakeBackend()
      ..on('GET', '/v1/pairs', {'title': 'Authentication failed'}, status: 401)
      ..on('POST', '/v1/auth/refresh', {
        'title': 'Authentication failed',
      }, status: 401);
    await pumpApp(tester, api, tokens: signedIn());

    expect(
      find.text('Learn a language with a friend who speaks it'),
      findsOneWidget,
    );
  });

  testWidgets('teaching a sentence sends it with its meaning', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api
      ..on('GET', '/v1/pairs/$pairId/contributions', <Object>[])
      ..on('GET', '/v1/pairs/$pairId/attempts', <Object>[])
      ..on('POST', '/v1/pairs/$pairId/contributions', {
        ..._contribution,
        'author_id': me,
        'learner_id': partner,
        'language': 'bs',
      }, status: 201);
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.textContaining('You teach'));
    expect(find.text('A sentence in bosanski'), findsOneWidget);
    expect(find.text('What it means in العربية'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('sentence')), ' Dobro jutro ');
    await tester.enterText(find.byKey(const Key('gloss')), 'صباح الخير');
    await tester.tapAndSettle(find.text('Add'));

    expect(api.bodyOf('POST /v1/pairs/$pairId/contributions'), {
      'text': 'Dobro jutro',
      'gloss': 'صباح الخير',
      'gloss_language': 'ar',
    });
    expect(find.text('Sentence added'), findsOneWidget);
  });

  testWidgets('the daily limit shows a friendly message', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api
      ..on('GET', '/v1/pairs/$pairId/contributions', <Object>[])
      ..on('GET', '/v1/pairs/$pairId/attempts', <Object>[])
      ..on('POST', '/v1/pairs/$pairId/contributions', {
        'title': 'Daily limit reached',
      }, status: 429);
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.textContaining('You teach'));
    await tester.enterText(find.byKey(const Key('sentence')), 'Dobro jutro');
    await tester.tapAndSettle(find.text('Add'));

    expect(find.textContaining('come back tomorrow'), findsOneWidget);
    expect(
      find.text('Daily limit reached'),
      findsNothing,
    ); // never raw server text
  });

  testWidgets('review: recall, reveal and rate each card', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api
      ..on('GET', '/v1/reviews/session', [
        {
          'id': 'k1',
          'item_id': 'c1',
          'due': '2026-11-05T00:00:00Z',
          'phase': 'learning',
          'is_new': true,
        },
      ])
      ..on('GET', '/v1/pairs/$pairId/contributions', [_contribution])
      ..on('GET', '/v1/pairs/$pairId/attempts', <Object>[])
      ..on('POST', '/v1/reviews/k1', {
        'id': 'k1',
        'item_id': 'c1',
        'due': '2026-11-06T00:00:00Z',
        'phase': 'review',
        'is_new': false,
      });
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.text('Review'));
    expect(find.text('What does it mean?'), findsOneWidget);
    final front = tester.widget<Text>(find.text('صباح الخير'));
    expect(front.textDirection, TextDirection.rtl);
    expect(find.text('Dobro jutro'), findsNothing);

    await tester.tapAndSettle(find.text('Show answer'));
    expect(find.text('Dobro jutro'), findsOneWidget);
    expect(find.text('Morning greeting'), findsOneWidget);

    await tester.tapAndSettle(find.byKey(const Key('rate-good')));
    expect(api.bodyOf('POST /v1/reviews/k1')['rating'], 3);
    expect(api.bodyOf('POST /v1/reviews/k1')['duration_ms'], isA<int>());
    expect(find.text('All done for now!'), findsOneWidget);
  });

  testWidgets('correcting a partner', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api
      ..on('GET', '/v1/attempts/to-review', [_attempt])
      ..on('POST', '/v1/attempts/a1/correction', {
        ..._attempt,
        'correction': {
          'corrected_text': 'Dobro sam',
          'comment': null,
          'corrected_at': '2026-11-05T10:00:00Z',
        },
      });
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.text('Correct your partner'));
    await tester.tapAndSettle(find.text('Ja sam dobro'));
    await tester.enterText(find.byKey(const Key('corrected')), 'Dobro sam');
    api.on('GET', '/v1/attempts/to-review', <Object>[]);
    await tester.tapAndSettle(find.text('Send correction'));

    expect(api.bodyOf('POST /v1/attempts/a1/correction'), {
      'corrected_text': 'Dobro sam',
    });
    expect(find.text('Nothing to correct right now.'), findsOneWidget);
  });

  testWidgets('joining with a code opens the new pair', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api
      ..on('GET', '/v1/pairs', <Object>[])
      ..on('POST', '/v1/invitations/accept', {
        'id': pairId,
        'created_at': '2026-11-01T10:00:00Z',
        'members': [
          {'user_id': partner, 'teaches': 'ar', 'learns': 'bs'},
          {'user_id': me, 'teaches': 'bs', 'learns': 'ar'},
        ],
      }, status: 201);
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.text('Join with a code'));
    await tester.tapAndSettle(find.widgetWithText(FilledButton, 'Join'));
    expect(find.text('Required'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('join-code')), ' ABC-123 ');
    seedPair(api);
    api
      ..on('GET', '/v1/pairs/$pairId/contributions', <Object>[])
      ..on('GET', '/v1/pairs/$pairId/attempts', <Object>[]);
    await tester.tapAndSettle(find.widgetWithText(FilledButton, 'Join'));

    expect(api.bodyOf('POST /v1/invitations/accept'), {'code': 'ABC-123'});
    expect(find.text('A sentence in bosanski'), findsOneWidget);
  });

  testWidgets('inviting shows the code once', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api.on('POST', '/v1/invitations', {
      'code': 'XYZ-789',
      'expires_in_days': 7,
    }, status: 201);
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.text('Invite a partner'));
    await tester.tapAndSettle(find.byKey(const Key('teaches')));
    await tester.tapAndSettle(find.text('bosanski (Bosnian)').last);
    await tester.tapAndSettle(find.byKey(const Key('learns')));
    await tester.tapAndSettle(find.text('bosanski (Bosnian)').last);
    expect(find.text('Pick two different languages.'), findsOneWidget);

    await tester.tapAndSettle(find.byKey(const Key('learns')));
    await tester.tapAndSettle(find.text('العربية (Arabic)').last);
    await tester.tapAndSettle(find.text('Create code'));

    expect(api.bodyOf('POST /v1/invitations'), {
      'teaches': 'bs',
      'learns': 'ar',
    });
    expect(find.text('XYZ-789'), findsOneWidget);
    expect(find.textContaining('expires in 7 days'), findsOneWidget);
  });

  group('in Arabic', () {
    setUp(() {
      TestWidgetsFlutterBinding.ensureInitialized()
          .platformDispatcher
          .localesTestValue = const [
        Locale('ar'),
      ];
    });
    tearDown(() {
      TestWidgetsFlutterBinding.ensureInitialized().platformDispatcher
          .clearLocalesTestValue();
    });

    testWidgets('the app is right-to-left with Arabic text and plurals', (
      tester,
    ) async {
      final api = FakeBackend();
      seedPair(api, streak: 2);
      await pumpApp(tester, api, tokens: signedIn());

      final context = tester.element(find.byType(Scaffold).first);
      expect(Directionality.of(context), TextDirection.rtl);
      expect(find.text('يومان متتاليان'), findsOneWidget);
      expect(find.text('المراجعة'), findsOneWidget);
    });
  });

  group('in Bosnian', () {
    setUp(() {
      TestWidgetsFlutterBinding.ensureInitialized()
          .platformDispatcher
          .localesTestValue = const [
        Locale('bs'),
      ];
    });
    tearDown(() {
      TestWidgetsFlutterBinding.ensureInitialized().platformDispatcher
          .clearLocalesTestValue();
    });

    testWidgets('uses Bosnian plural forms', (tester) async {
      final api = FakeBackend();
      seedPair(api, streak: 3);
      await pumpApp(tester, api, tokens: signedIn());

      expect(find.text('Niz: 3 dana'), findsOneWidget);
      expect(find.text('Ponavljanje'), findsOneWidget);
    });
  });
}
