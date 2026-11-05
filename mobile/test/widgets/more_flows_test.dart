import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:langex/app/providers.dart';
import 'package:langex/core/auth/session.dart';
import 'package:langex/core/auth/token_store.dart';

import '../support/fakes.dart';

void main() {
  testWidgets('practising: send a sentence, then see the correction', (
    tester,
  ) async {
    final api = FakeBackend();
    seedPair(api);
    api
      ..on('GET', '/v1/pairs/$pairId/contributions', <Object>[])
      ..on('GET', '/v1/pairs/$pairId/attempts', [
        {
          'id': 'a1',
          'pair_id': pairId,
          'learner_id': me,
          'reviewer_id': partner,
          'language': 'ar',
          'text': 'انا بخير',
          'created_at': '2026-11-05T09:00:00Z',
          'correction': {
            'corrected_text': 'أنا بخير',
            'comment': 'Hamza on alif',
            'corrected_at': '2026-11-05T10:00:00Z',
          },
        },
      ])
      ..on('POST', '/v1/pairs/$pairId/attempts', {
        'id': 'a2',
        'pair_id': pairId,
        'learner_id': me,
        'reviewer_id': partner,
        'language': 'ar',
        'text': 'شكرا',
        'created_at': '2026-11-05T11:00:00Z',
        'correction': null,
      }, status: 201);
    await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.textContaining('You teach'));
    await tester.tapAndSettle(find.text('Practise'));
    expect(find.text('أنا بخير'), findsOneWidget);
    expect(find.text('Hamza on alif'), findsOneWidget);
    final field = tester.widget<EditableText>(
      find.descendant(
        of: find.byKey(const Key('attempt')),
        matching: find.byType(EditableText),
      ),
    );
    expect(field.textDirection, TextDirection.rtl);

    await tester.tapAndSettle(find.text('Send'));
    expect(find.text('Required'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('attempt')), 'شكرا');
    await tester.tapAndSettle(find.text('Send'));

    expect(api.bodyOf('POST /v1/pairs/$pairId/attempts'), {'text': 'شكرا'});
    expect(find.text('Sent to your partner'), findsOneWidget);
  });

  testWidgets('signing out revokes the session on the server', (tester) async {
    final api = FakeBackend();
    seedPair(api);
    api.on('POST', '/v1/auth/sign-out', null, status: 204);
    final container = await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.byType(PopupMenuButton<void>));
    await tester.tapAndSettle(find.text('Sign out'));

    expect(api.bodyOf('POST /v1/auth/sign-out'), {
      'refresh_token': 'refresh-1',
    });
    expect(container.read(sessionProvider).status, SessionStatus.signedOut);
    expect(
      find.text('Learn a language with a friend who speaks it'),
      findsOneWidget,
    );
  });

  testWidgets('signing out offline still forgets the session here', (
    tester,
  ) async {
    final api = FakeBackend();
    seedPair(api);
    api.onCall(
      'POST',
      '/v1/auth/sign-out',
      (_) => throw http.ClientException('offline'),
    );
    final container = await pumpApp(tester, api, tokens: signedIn());

    await tester.tapAndSettle(find.byType(PopupMenuButton<void>));
    await tester.tapAndSettle(find.text('Sign out'));

    expect(container.read(sessionProvider).status, SessionStatus.signedOut);
  });

  testWidgets('a failed load can be retried', (tester) async {
    final api = FakeBackend()
      ..onCall(
        'GET',
        '/v1/pairs',
        (_) => throw http.ClientException('offline'),
      );
    await pumpApp(tester, api, tokens: signedIn());

    expect(find.text('No connection. Try again.'), findsOneWidget);
    seedPair(api);
    await tester.tapAndSettle(find.text('Try again'));
    expect(find.textContaining('You teach'), findsOneWidget);
  });

  group('SecureTokenStore', () {
    test('round trip, and clear', () async {
      FlutterSecureStorage.setMockInitialValues({});
      final store = SecureTokenStore();
      expect(await store.read(), isNull);
      await store.write(signedIn());
      expect((await store.read())?.refreshToken, 'refresh-1');
      await store.clear();
      expect(await store.read(), isNull);
    });

    test('an unreadable entry is dropped, not a crash', () async {
      FlutterSecureStorage.setMockInitialValues({
        'langex.session': '{not json',
      });
      final store = SecureTokenStore();
      expect(await store.read(), isNull);
      FlutterSecureStorage.setMockInitialValues({});
    });
  });
}
