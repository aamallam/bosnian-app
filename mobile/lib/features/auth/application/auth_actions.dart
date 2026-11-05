import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/auth/session.dart';
import '../data/auth_api.dart';

class AuthActions {
  AuthActions(this._api, this._session);
  final AuthApi _api;
  final Session _session;

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
    }
  }
}

final authActionsProvider = Provider<AuthActions>(
  (ref) => AuthActions(ref.watch(authApiProvider), ref.watch(sessionProvider)),
);
