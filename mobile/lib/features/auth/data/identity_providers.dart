import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import 'auth_api.dart';

/// The provider's sign-in did not produce a usable ID token (configuration
/// problem, no network, provider error). Cancelling is not an error.
class SignInFailed implements Exception {
  const SignInFailed(this.reason);
  final String reason; // for logs only

  @override
  String toString() => 'SignInFailed($reason)';
}

/// A way to prove who the user is (Apple, Google). It asks the platform for
/// an ID token that carries [nonce]; our server checks both.
abstract interface class IdentityProvider {
  /// `apple` or `google`, as the API names them.
  String get id;

  /// Null when the user cancelled.
  Future<SignInCredential?> obtain(String nonce);

  /// Forgets the account chosen on this device, so the next sign-in can pick
  /// another one (shared phones).
  Future<void> forget();
}

class GoogleIdentityProvider implements IdentityProvider {
  GoogleIdentityProvider({required this.serverClientId, this.iosClientId});

  /// The *web* OAuth client ID: Google issues the ID token for it, so it must
  /// be in the server's LANGEX_GOOGLE_CLIENT_IDS.
  final String serverClientId;

  /// iOS only: the iOS OAuth client ID.
  final String? iosClientId;

  @override
  String get id => 'google';

  @override
  Future<SignInCredential?> obtain(String nonce) async {
    final google = GoogleSignIn.instance;
    // The platform implementations keep the nonce from the latest
    // initialize(), which lets every attempt carry a fresh server nonce.
    await google.initialize(
      clientId: iosClientId,
      serverClientId: serverClientId,
      nonce: nonce,
    );
    if (!google.supportsAuthenticate()) {
      throw const SignInFailed('authenticate() not supported here');
    }
    try {
      final account = await google.authenticate();
      final idToken = account.authentication.idToken;
      if (idToken == null) throw const SignInFailed('no ID token');
      return SignInCredential(provider: id, idToken: idToken, nonce: nonce);
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled) return null;
      throw SignInFailed('google: ${e.code.name}');
    }
  }

  @override
  Future<void> forget() => GoogleSignIn.instance.signOut();
}

typedef AppleCredentialRequest =
    Future<AuthorizationCredentialAppleID> Function(String nonce);

/// Sign in with Apple (iOS). Needs the paid Apple Developer Program and the
/// capability on the app ID; offered only when APPLE_SIGN_IN=true.
class AppleIdentityProvider implements IdentityProvider {
  AppleIdentityProvider({AppleCredentialRequest? request})
    : _request = request ?? _platformRequest;

  final AppleCredentialRequest _request;

  static Future<AuthorizationCredentialAppleID> _platformRequest(
    String nonce,
  ) => SignInWithApple.getAppleIDCredential(
    // No name or email: we store only Apple's opaque subject (ADR 0007).
    scopes: const [],
    nonce: nonce,
  );

  @override
  String get id => 'apple';

  @override
  Future<SignInCredential?> obtain(String nonce) async {
    try {
      final credential = await _request(nonce);
      final token = credential.identityToken;
      if (token == null) throw const SignInFailed('no identity token');
      return SignInCredential(provider: id, idToken: token, nonce: nonce);
    } on SignInWithAppleAuthorizationException catch (e) {
      if (e.code == AuthorizationErrorCode.canceled) return null;
      throw SignInFailed('apple: ${e.code.name}');
    }
  }

  @override
  Future<void> forget() async {} // Apple keeps no session in the app
}
