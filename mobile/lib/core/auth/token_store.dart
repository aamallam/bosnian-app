import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// What the device keeps after sign-in. Only in the Keychain / Keystore,
/// never in shared preferences or logs.
class Tokens {
  const Tokens({
    required this.accessToken,
    required this.refreshToken,
    required this.accessExpiresAt,
    required this.accountId,
  });

  factory Tokens.fromJson(Map<String, Object?> json) => Tokens(
    accessToken: json['access_token']! as String,
    refreshToken: json['refresh_token']! as String,
    accessExpiresAt: DateTime.parse(json['access_expires_at']! as String),
    accountId: json['account_id']! as String,
  );

  final String accessToken;
  final String refreshToken;
  final DateTime accessExpiresAt;
  final String accountId;

  Map<String, Object?> toJson() => {
    'access_token': accessToken,
    'refresh_token': refreshToken,
    'access_expires_at': accessExpiresAt.toUtc().toIso8601String(),
    'account_id': accountId,
  };

  @override
  String toString() => 'Tokens(account: $accountId)'; // never print tokens
}

abstract interface class TokenStore {
  Future<Tokens?> read();
  Future<void> write(Tokens tokens);
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage])
    : _storage =
          storage ??
          const FlutterSecureStorage(
            // Readable after the first unlock (background sync), and never
            // copied to another device through backups.
            iOptions: IOSOptions(
              accessibility: KeychainAccessibility.first_unlock_this_device,
            ),
          );

  static const _key = 'langex.session';
  final FlutterSecureStorage _storage;

  @override
  Future<Tokens?> read() async {
    final raw = await _storage.read(key: _key);
    if (raw == null) return null;
    try {
      return Tokens.fromJson(jsonDecode(raw) as Map<String, Object?>);
    } on Object {
      await clear(); // unreadable (older format): start signed out
      return null;
    }
  }

  @override
  Future<void> write(Tokens tokens) =>
      _storage.write(key: _key, value: jsonEncode(tokens.toJson()));

  @override
  Future<void> clear() => _storage.delete(key: _key);
}

/// For tests and previews.
class MemoryTokenStore implements TokenStore {
  MemoryTokenStore([this._tokens]);
  Tokens? _tokens;

  @override
  Future<Tokens?> read() async => _tokens;

  @override
  Future<void> write(Tokens tokens) async => _tokens = tokens;

  @override
  Future<void> clear() async => _tokens = null;
}
