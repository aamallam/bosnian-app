import 'dart:async';

import 'package:flutter/foundation.dart';

import '../api/api_exception.dart';
import 'token_store.dart';

enum SessionStatus { loading, signedOut, signedIn }

/// Exchanges a refresh token for new tokens. Throws [ApiException] with
/// [ApiErrorKind.unauthorized] when the server refuses it.
typedef Refresher = Future<Tokens> Function(String refreshToken);

/// The signed-in state of this device. The router listens to it; the API
/// client asks it for access tokens.
class Session extends ChangeNotifier {
  Session(this._store, this._refresher, {DateTime Function()? now})
    : _now = now ?? DateTime.now;

  /// Refresh a little before expiry, so requests do not fail on the way.
  static const refreshMargin = Duration(seconds: 60);

  final TokenStore _store;
  final Refresher _refresher;
  final DateTime Function() _now;

  Tokens? _tokens;
  Future<Tokens?>? _refreshing;
  SessionStatus _status = SessionStatus.loading;

  SessionStatus get status => _status;
  String? get accountId => _tokens?.accountId;

  Future<void> restore() async {
    _tokens = await _store.read();
    _setStatus(
      _tokens == null ? SessionStatus.signedOut : SessionStatus.signedIn,
    );
  }

  Future<void> start(Tokens tokens) async {
    await _store.write(tokens);
    _tokens = tokens;
    _setStatus(SessionStatus.signedIn);
  }

  /// Forgets the tokens on this device (the caller revokes them first).
  Future<void> end() async {
    _tokens = null;
    await _store.clear();
    _setStatus(SessionStatus.signedOut);
  }

  String? get refreshToken => _tokens?.refreshToken;

  /// A usable access token, refreshed first when it is about to expire.
  Future<String?> accessToken() async {
    final tokens = _tokens;
    if (tokens == null) return null;
    if (_now().toUtc().add(refreshMargin).isBefore(tokens.accessExpiresAt)) {
      return tokens.accessToken;
    }
    return (await _refresh())?.accessToken;
  }

  /// Called after a 401. If another request already refreshed, its new token
  /// is reused, so parallel requests never spend the refresh token twice
  /// (which the server treats as theft and answers by signing out).
  Future<String?> refreshAfterRejection(String rejectedAccessToken) async {
    final tokens = _tokens;
    if (tokens == null) return null;
    if (tokens.accessToken != rejectedAccessToken) return tokens.accessToken;
    return (await _refresh())?.accessToken;
  }

  Future<Tokens?> _refresh() =>
      _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);

  Future<Tokens?> _doRefresh() async {
    final current = _tokens;
    if (current == null) return null;
    try {
      final fresh = await _refresher(current.refreshToken);
      await start(fresh);
      return fresh;
    } on ApiException catch (e) {
      if (e.kind == ApiErrorKind.unauthorized ||
          e.kind == ApiErrorKind.invalid) {
        await end();
        return null;
      }
      rethrow; // offline: keep the tokens and try again later
    }
  }

  void _setStatus(SessionStatus status) {
    _status = status;
    notifyListeners();
  }
}
