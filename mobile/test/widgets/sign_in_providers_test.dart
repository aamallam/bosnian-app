import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langex/app/providers.dart';
import 'package:langex/core/auth/session.dart';

import '../support/fakes.dart';

const _tokens = {
  'access_token': 'a',
  'refresh_token': 'r',
  'token_type': 'bearer',
  'expires_in': 900,
  'account_id': me,
  'is_new_account': true,
};

FakeBackend _backend() => FakeBackend()
  ..on('POST', '/v1/auth/nonce', {'nonce': 'server-nonce-1', 'expires_in': 600})
  ..on('POST', '/v1/auth/sign-in', _tokens)
  ..on('GET', '/v1/pairs', <Object>[])
  ..on('GET', '/v1/languages', <Object>[]);

void main() {
  testWidgets('Google sign-in uses a fresh server nonce', (tester) async {
    final api = _backend();
    final google = FakeIdentityProvider();
    final container = await pumpApp(
      tester,
      api,
      devSignIn: false,
      identity: [google],
    );

    expect(
      find.text("Sign-in isn't available in this build yet."),
      findsNothing,
    );
    await tester.tapAndSettle(find.text('Continue with Google'));

    expect(google.nonces, ['server-nonce-1']);
    expect(api.bodyOf('POST /v1/auth/sign-in'), {
      'provider': 'google',
      'id_token': 'google-token:server-nonce-1',
      'nonce': 'server-nonce-1',
    });
    expect(container.read(sessionProvider).status, SessionStatus.signedIn);
    expect(find.text('Start with a partner'), findsOneWidget);
  });

  testWidgets('cancelling stays on the sign-in screen quietly', (tester) async {
    final api = _backend();
    await pumpApp(
      tester,
      api,
      devSignIn: false,
      identity: [FakeIdentityProvider(result: 'cancel')],
    );

    await tester.tapAndSettle(find.text('Continue with Google'));

    expect(api.calls, isNot(contains('POST /v1/auth/sign-in')));
    expect(find.byType(SnackBar), findsNothing);
    expect(find.text('Continue with Google'), findsOneWidget);
  });

  testWidgets('a provider failure shows a message', (tester) async {
    await pumpApp(
      tester,
      _backend(),
      devSignIn: false,
      identity: [FakeIdentityProvider(result: 'fail')],
    );

    await tester.tapAndSettle(find.text('Continue with Google'));

    expect(find.text("Sign-in didn't work. Try again."), findsOneWidget);
  });

  testWidgets('the server refusing the token shows the session message', (
    tester,
  ) async {
    final api = _backend()
      ..on('POST', '/v1/auth/sign-in', {
        'title': 'Authentication failed',
      }, status: 401);
    await pumpApp(
      tester,
      api,
      devSignIn: false,
      identity: [FakeIdentityProvider()],
    );

    await tester.tapAndSettle(find.text('Continue with Google'));

    expect(find.text('Please sign in again.'), findsOneWidget);
  });

  testWidgets('Apple first, then Google, then the dev form', (tester) async {
    await pumpApp(
      tester,
      _backend(),
      identity: [
        FakeIdentityProvider(id: 'apple'),
        FakeIdentityProvider(),
      ],
    );

    final apple = tester.getTopLeft(find.text('Continue with Apple')).dy;
    final google = tester.getTopLeft(find.text('Continue with Google')).dy;
    final dev = tester.getTopLeft(find.byKey(const Key('dev-name'))).dy;
    expect(apple < google && google < dev, isTrue);
    expect(find.text('Development server'), findsOneWidget);
  });

  testWidgets('signing out also forgets the Google account here', (
    tester,
  ) async {
    final api = _backend()..on('POST', '/v1/auth/sign-out', null, status: 204);
    seedPair(api);
    final google = FakeIdentityProvider();
    await pumpApp(tester, api, tokens: signedIn(), identity: [google]);

    await tester.tapAndSettle(find.byType(PopupMenuButton<void>));
    await tester.tapAndSettle(find.text('Sign out'));

    expect(google.forgotten, 1);
  });
}
