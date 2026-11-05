import '../../../core/api/api_client.dart';
import '../../../core/json.dart';
import '../domain/models.dart';

class PairingApi {
  PairingApi(this._client);
  final ApiClient _client;

  Future<Invitation> invite({
    required String teaches,
    required String learns,
  }) async => Invitation.fromJson(
    asJson(
      await _client.post(
        '/v1/invitations',
        body: {'teaches': teaches, 'learns': learns},
      ),
    ),
  );

  Future<Pair> accept(String code) async => Pair.fromJson(
    asJson(
      await _client.post('/v1/invitations/accept', body: {'code': code.trim()}),
    ),
  );

  Future<List<Pair>> pairs() async =>
      asJsonList(await _client.get('/v1/pairs')).map(Pair.fromJson).toList();

  Future<Contribution> contribute(
    String pairId, {
    required String text,
    String? gloss,
    String? glossLanguage,
    String? note,
  }) async => Contribution.fromJson(
    asJson(
      await _client.post(
        '/v1/pairs/${Uri.encodeComponent(pairId)}/contributions',
        body: {
          'text': text,
          'gloss': ?gloss,
          if (gloss != null && glossLanguage != null)
            'gloss_language': glossLanguage,
          'note': ?note,
        },
      ),
    ),
  );

  Future<List<Contribution>> contributions(
    String pairId, {
    DateTime? since,
  }) async => asJsonList(
    await _client.get(
      '/v1/pairs/${Uri.encodeComponent(pairId)}/contributions',
      query: since == null ? null : {'since': since.toUtc().toIso8601String()},
    ),
  ).map(Contribution.fromJson).toList();

  Future<Attempt> submitAttempt(String pairId, String text) async =>
      Attempt.fromJson(
        asJson(
          await _client.post(
            '/v1/pairs/${Uri.encodeComponent(pairId)}/attempts',
            body: {'text': text},
          ),
        ),
      );

  /// My own attempts in this pair, with corrections once given.
  Future<List<Attempt>> myAttempts(String pairId) async => asJsonList(
    await _client.get('/v1/pairs/${Uri.encodeComponent(pairId)}/attempts'),
  ).map(Attempt.fromJson).toList();

  Future<int> streak(String pairId) async => asJson(
    await _client.get('/v1/pairs/${Uri.encodeComponent(pairId)}/streak'),
  ).integer('days');

  /// Attempts my partners wrote that wait for my correction.
  Future<List<Attempt>> toReview() async =>
      asJsonList(await _client.get('/v1/attempts/to-review'))
          .map(Attempt.fromJson)
          .toList();

  Future<Attempt> correct(
    String attemptId, {
    required String correctedText,
    String? comment,
  }) async => Attempt.fromJson(
    asJson(
      await _client.post(
        '/v1/attempts/${Uri.encodeComponent(attemptId)}/correction',
        body: {'corrected_text': correctedText, 'comment': ?comment},
      ),
    ),
  );
}
