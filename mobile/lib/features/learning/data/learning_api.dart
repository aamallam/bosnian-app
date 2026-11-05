import '../../../core/api/api_client.dart';
import '../../../core/json.dart';
import '../domain/review_card.dart';

class LearningApi {
  LearningApi(this._client);
  final ApiClient _client;

  /// Due cards first, then today's new ones.
  Future<List<ReviewCard>> session() async =>
      asJsonList(await _client.get('/v1/reviews/session'))
          .map(ReviewCard.fromJson)
          .toList();

  Future<ReviewCard> review(
    String cardId,
    Rating rating, {
    Duration? took,
  }) async => ReviewCard.fromJson(
    asJson(
      await _client.post(
        '/v1/reviews/${Uri.encodeComponent(cardId)}',
        body: {
          'rating': rating.value,
          if (took != null)
            'duration_ms': took.inMilliseconds.clamp(0, 3600000),
        },
      ),
    ),
  );
}
