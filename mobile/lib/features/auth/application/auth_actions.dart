import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/auth/session.dart';
import '../data/auth_api.dart';
import '../data/identity_providers.dart';

class AuthActions {
  AuthActions(this._api, this._session, this._providers);
  final AuthApi _api;
  final Session _session;
  final List<IdentityProvider> _providers;

  /// Signs in with Apple or Google. Returns false when the user cancelled.
  Future<bool> signInWith(IdentityProvider provider) async {
    final credential = await provider.obtain(await _api.nonce());
    if (credential == null) return false;
    await signIn(credential);
    return true;
  }

  Future<void> signIn(SignInCredential credential) async {
    await _session.start(await _api.signIn(credential));
  }

  /// Revokes the tokens on the server when it can be reached; the device
  /// forgets them either way.
  Future<void> signOut() async {
    final refreshToken = _session.refreshToken;
    try {
      if (refreshToken != null) await _api.signOut(refreshToken);
    } on Exception {
      // offline: the refresh token still expires on the server
    } finally {
      await _session.end();
      for (final provider in _providers) {
        try {
          await provider.forget();
        } on Exception {
          // nothing to forget, or the plugin is unavailable
        }
      }
    }
  }
}

final authActionsProvider = Provider<AuthActions>(
  (ref) => AuthActions(
    ref.watch(authApiProvider),
    ref.watch(sessionProvider),
    ref.watch(identityProvidersProvider),
  ),
);
