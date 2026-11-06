import '../../../core/api/api_client.dart';
import '../../../core/auth/token_store.dart';
import '../../../core/json.dart';

/// What a sign-in provider hands over: an ID token for our server to verify.
class SignInCredential {
  const SignInCredential({
    required this.provider,
    required this.idToken,
    this.nonce,
  });

  /// Development servers only: `dev:<name>` signs in as that name.
  factory SignInCredential.dev(String name) =>
      SignInCredential(provider: 'dev', idToken: 'dev:${name.trim()}');

  /// `apple`, `google` or `dev`.
  final String provider;
  final String idToken;

  /// The random value given to the provider; Apple and Google tokens must
  /// carry it back, so a stolen token cannot be replayed here.
  final String? nonce;
}

/// The auth endpoints. Uses a client without a session: these calls are how
/// a session starts and ends.
class AuthApi {
  AuthApi(this._client, {DateTime Function()? now})
    : _now = now ?? DateTime.now;

  final ApiClient _client;
  final DateTime Function() _now;

  /// A single-use value for the next Apple or Google sign-in (10 minutes).
  Future<String> nonce() async =>
      asJson(await _client.post('/v1/auth/nonce')).str('nonce');

  Future<Tokens> signIn(SignInCredential credential) async => _tokens(
    await _client.post(
      '/v1/auth/sign-in',
      body: {
        'provider': credential.provider,
        'id_token': credential.idToken,
        if (credential.nonce != null) 'nonce': credential.nonce,
      },
    ),
  );

  Future<Tokens> refresh(String refreshToken) async => _tokens(
    await _client.post(
      '/v1/auth/refresh',
      body: {'refresh_token': refreshToken},
    ),
  );

  Future<void> signOut(String refreshToken) async {
    await _client.post(
      '/v1/auth/sign-out',
      body: {'refresh_token': refreshToken},
    );
  }

  Tokens _tokens(Object? answer) {
    final json = asJson(answer);
    return Tokens(
      accessToken: json.str('access_token'),
      refreshToken: json.str('refresh_token'),
      accessExpiresAt: _now().toUtc().add(
        Duration(seconds: json.integer('expires_in')),
      ),
      accountId: json.str('account_id'),
    );
  }
}
