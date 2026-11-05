import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import '../core/api/api_client.dart';
import '../core/auth/session.dart';
import '../core/auth/token_store.dart';
import '../core/config.dart';
import '../features/auth/data/auth_api.dart';
import '../features/languages/language.dart';
import '../features/learning/data/learning_api.dart';
import '../features/pairing/data/pairing_api.dart';

/// Composition root of the app: the only place that picks implementations.
/// Tests override [configProvider], [httpClientProvider] and
/// [tokenStoreProvider].
final configProvider = Provider<AppConfig>(
  (ref) => throw UnimplementedError('Overridden in main()'),
);

final httpClientProvider = Provider<http.Client>((ref) {
  final client = http.Client();
  ref.onDispose(client.close);
  return client;
});

final tokenStoreProvider = Provider<TokenStore>((ref) => SecureTokenStore());

final authApiProvider = Provider<AuthApi>(
  (ref) => AuthApi(
    ApiClient(
      baseUrl: ref.watch(configProvider).apiBaseUrl,
      client: ref.watch(httpClientProvider),
    ),
  ),
);

final sessionProvider = Provider<Session>((ref) {
  final session = Session(
    ref.watch(tokenStoreProvider),
    ref.watch(authApiProvider).refresh,
  );
  ref.onDispose(session.dispose);
  return session;
});

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(
    baseUrl: ref.watch(configProvider).apiBaseUrl,
    client: ref.watch(httpClientProvider),
    session: ref.watch(sessionProvider),
  ),
);

final languagesApiProvider = Provider<LanguagesApi>(
  (ref) => LanguagesApi(ref.watch(apiClientProvider)),
);

final pairingApiProvider = Provider<PairingApi>(
  (ref) => PairingApi(ref.watch(apiClientProvider)),
);

final learningApiProvider = Provider<LearningApi>(
  (ref) => LearningApi(ref.watch(apiClientProvider)),
);
