import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';
import 'package:langex/features/auth/data/identity_providers.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

/// Stands in for the native Google Sign-In plugin.
class _FakeGooglePlatform extends GoogleSignInPlatform
    with MockPlatformInterfaceMixin {
  final inits = <InitParameters>[];
  Object? fail;
  String? idToken = 'google-id-token';
  int signOuts = 0;

  @override
  Future<void> init(InitParameters params) async => inits.add(params);

  @override
  bool supportsAuthenticate() => true;

  @override
  Future<AuthenticationResults> authenticate(
    AuthenticateParameters params,
  ) async {
    if (fail case final Object error) throw error;
    return AuthenticationResults(
      user: const GoogleSignInUserData(email: 'a@example.com', id: '1'),
      authenticationTokens: AuthenticationTokenData(idToken: idToken),
    );
  }

  @override
  Future<void> signOut(SignOutParams params) async => signOuts++;

  @override
  Future<AuthenticationResults?>? attemptLightweightAuthentication(
    AttemptLightweightAuthenticationParameters params,
  ) => null;

  @override
  bool authorizationRequiresUserInteraction() => false;

  @override
  Future<ClientAuthorizationTokenData?> clientAuthorizationTokensForScopes(
    ClientAuthorizationTokensForScopesParameters params,
  ) async => null;

  @override
  Future<ServerAuthorizationTokenData?> serverAuthorizationTokensForScopes(
    ServerAuthorizationTokensForScopesParameters params,
  ) async => null;

  @override
  Future<void> disconnect(DisconnectParams params) async {}
}

AuthorizationCredentialAppleID _apple(String? token) =>
    AuthorizationCredentialAppleID(
      userIdentifier: 'u',
      givenName: null,
      familyName: null,
      authorizationCode: 'code',
      email: null,
      identityToken: token,
      state: null,
    );

void main() {
  group('Google', () {
    late _FakeGooglePlatform platform;
    setUp(
      () => GoogleSignInPlatform.instance = platform = _FakeGooglePlatform(),
    );

    test('each attempt carries the server nonce and our client IDs', () async {
      final google = GoogleIdentityProvider(
        serverClientId: 'web.apps.googleusercontent.com',
        iosClientId: 'ios.apps.googleusercontent.com',
      );

      final first = await google.obtain('nonce-1');
      await google.obtain('nonce-2');

      expect(first?.provider, 'google');
      expect(first?.idToken, 'google-id-token');
      expect(first?.nonce, 'nonce-1');
      expect(platform.inits.map((i) => i.nonce), ['nonce-1', 'nonce-2']);
      expect(
        platform.inits.first.serverClientId,
        'web.apps.googleusercontent.com',
      );
      expect(platform.inits.first.clientId, 'ios.apps.googleusercontent.com');
    });

    test('cancelling is not an error', () async {
      platform.fail = const GoogleSignInException(
        code: GoogleSignInExceptionCode.canceled,
      );
      expect(
        await GoogleIdentityProvider(serverClientId: 'w').obtain('n'),
        isNull,
      );
    });

    test('provider errors and a missing ID token fail', () async {
      final google = GoogleIdentityProvider(serverClientId: 'w');
      platform.fail = const GoogleSignInException(
        code: GoogleSignInExceptionCode.clientConfigurationError,
      );
      await expectLater(google.obtain('n'), throwsA(isA<SignInFailed>()));

      platform
        ..fail = null
        ..idToken = null;
      await expectLater(google.obtain('n'), throwsA(isA<SignInFailed>()));
    });

    test('forget signs out of Google on this device', () async {
      await GoogleIdentityProvider(serverClientId: 'w').forget();
      expect(platform.signOuts, 1);
    });
  });

  group('Apple', () {
    test('passes the nonce and asks for no name or email', () async {
      String? sent;
      final apple = AppleIdentityProvider(
        request: (nonce) async {
          sent = nonce;
          return _apple('apple-id-token');
        },
      );

      final credential = await apple.obtain('nonce-1');

      expect(sent, 'nonce-1');
      expect(credential?.provider, 'apple');
      expect(credential?.idToken, 'apple-id-token');
      expect(credential?.nonce, 'nonce-1');
      await apple.forget();
    });

    test('cancelling is not an error; other failures are', () async {
      Never fail(AuthorizationErrorCode code) =>
          throw SignInWithAppleAuthorizationException(code: code, message: 'x');

      expect(
        await AppleIdentityProvider(
          request: (_) async => fail(AuthorizationErrorCode.canceled),
        ).obtain('n'),
        isNull,
      );
      await expectLater(
        AppleIdentityProvider(
          request: (_) async => fail(AuthorizationErrorCode.failed),
        ).obtain('n'),
        throwsA(isA<SignInFailed>()),
      );
      await expectLater(
        AppleIdentityProvider(request: (_) async => _apple(null)).obtain('n'),
        throwsA(isA<SignInFailed>()),
      );
    });
  });
}
