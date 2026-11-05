import 'package:flutter_test/flutter_test.dart';
import 'package:langex/core/api/api_exception.dart';
import 'package:langex/core/auth/token_store.dart';
import 'package:langex/core/config.dart';
import 'package:langex/core/json.dart';
import 'package:langex/features/learning/domain/review_card.dart';
import 'package:langex/features/pairing/domain/models.dart';
import 'package:langex/main.dart' show retryOnlyNetworkErrors;

void main() {
  group('AppConfig', () {
    test('accepts https and local development http', () {
      expect(
        AppConfig(apiBaseUrl: Uri.parse('https://api.example.com'))
            .apiBaseUrl
            .host,
        'api.example.com',
      );
      for (final local in [
        'http://10.0.2.2:8000',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
      ]) {
        expect(() => AppConfig(apiBaseUrl: Uri.parse(local)), returnsNormally);
      }
    });

    test('refuses plain http to anything else, and relative URLs', () {
      expect(
        () => AppConfig(apiBaseUrl: Uri.parse('http://api.example.com')),
        throwsArgumentError,
      );
      expect(
        () => AppConfig(apiBaseUrl: Uri.parse('/v1')),
        throwsArgumentError,
      );
      expect(
        () => AppConfig(apiBaseUrl: Uri.parse('ftp://localhost')),
        throwsArgumentError,
      );
    });

    test(
      'the default build points at the emulator host without dev sign-in',
      () {
        final config = AppConfig.fromEnvironment();
        expect(config.apiBaseUrl.toString(), 'http://10.0.2.2:8000');
        expect(config.devSignIn, isFalse);
      },
    );
  });

  test('tokens survive storage and never print', () async {
    final store = MemoryTokenStore();
    final tokens = Tokens(
      accessToken: 'secret-access',
      refreshToken: 'secret-refresh',
      accessExpiresAt: DateTime.utc(2026, 11, 5, 12),
      accountId: 'acc',
    );
    final copy = Tokens.fromJson(tokens.toJson());
    expect(copy.refreshToken, 'secret-refresh');
    expect(copy.accessExpiresAt, tokens.accessExpiresAt);
    expect(tokens.toString(), isNot(contains('secret')));
    await store.write(tokens);
    await store.clear();
    expect(await store.read(), isNull);
  });

  test('JSON readers fail loudly on a wrong shape', () {
    final Json json = {'id': 7, 'text': null};
    expect(() => json.str('id'), throwsFormatException);
    expect(json.strOrNull('text'), isNull);
    expect(() => json.str('missing'), throwsFormatException);
    expect(() => asJson([1]), throwsFormatException);
    expect(() => asJsonList({}), throwsFormatException);
    expect(
      Json.from({'t': '2026-11-05T10:00:00+01:00'}).time('t'),
      DateTime.utc(2026, 11, 5, 9),
    );
    expect(Json.from({'t': null}).timeOrNull('t'), isNull);
  });

  test('only network errors are retried, with back-off', () {
    const offline = ApiException(ApiErrorKind.network);
    expect(retryOnlyNetworkErrors(0, offline), const Duration(seconds: 1));
    expect(retryOnlyNetworkErrors(2, offline), const Duration(seconds: 4));
    expect(retryOnlyNetworkErrors(3, offline), isNull);
    expect(retryOnlyNetworkErrors(0, ApiException.fromStatus(404)), isNull);
    expect(retryOnlyNetworkErrors(0, StateError('bug')), isNull);
  });

  group('ReviewItem.resolve', () {
    ReviewCard card(String item) => ReviewCard(
      id: 'card-$item',
      itemId: item,
      due: DateTime.utc(2026),
      phase: 'learning',
      isNew: true,
    );
    final contribution = Contribution(
      id: 'c1',
      pairId: 'p',
      authorId: 'partner',
      learnerId: 'me',
      language: 'ar',
      text: 'صباح الخير',
      createdAt: DateTime.utc(2026),
      gloss: 'Dobro jutro',
      glossLanguage: 'bs',
      note: 'Morning greeting',
    );
    final corrected = Attempt(
      id: 'a1',
      pairId: 'p',
      learnerId: 'me',
      reviewerId: 'partner',
      language: 'ar',
      text: 'صباح النور',
      createdAt: DateTime.utc(2026),
      correction: Correction(
        correctedText: 'صباحُ النور',
        comment: 'Vowel',
        correctedAt: DateTime.utc(2026),
      ),
    );
    final waiting = Attempt(
      id: 'a2',
      pairId: 'p',
      learnerId: 'me',
      reviewerId: 'partner',
      language: 'ar',
      text: 'x',
      createdAt: DateTime.utc(2026),
    );

    test(
      'taught sentences ask for the meaning; corrections for the right form',
      () {
        final items = ReviewItem.resolve(
          [card('c1'), card('a1'), card('a2'), card('gone')],
          contributions: [contribution],
          attempts: [corrected, waiting],
        );

        expect(items.map((i) => i.kind), [
          PromptKind.taught,
          PromptKind.corrected,
        ]);
        expect(items[0].front, 'صباح الخير');
        expect(items[0].back, 'Dobro jutro');
        expect(items[0].backLanguage, 'bs');
        expect(items[1].front, 'صباح النور');
        expect(items[1].back, 'صباحُ النور');
        expect(items[1].note, 'Vowel');
      },
    );
  });

  test('pair members', () {
    final pair = Pair.fromJson({
      'id': 'p',
      'created_at': '2026-11-01T10:00:00Z',
      'members': [
        {'user_id': 'me', 'teaches': 'bs', 'learns': 'ar'},
        {'user_id': 'you', 'teaches': 'ar', 'learns': 'bs'},
      ],
    });
    expect(pair.me('me').teaches, 'bs');
    expect(pair.partnerOf('me').userId, 'you');
  });
}
