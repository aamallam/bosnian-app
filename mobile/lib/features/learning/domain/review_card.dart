import '../../../core/json.dart';
import '../../pairing/domain/models.dart';

/// How well the learner remembered (FSRS ratings).
enum Rating {
  again(1),
  hard(2),
  good(3),
  easy(4);

  const Rating(this.value);
  final int value;
}

class ReviewCard {
  const ReviewCard({
    required this.id,
    required this.itemId,
    required this.due,
    required this.phase,
    required this.isNew,
  });

  factory ReviewCard.fromJson(Json json) => ReviewCard(
    id: json.str('id'),
    itemId: json.str('item_id'),
    due: json.time('due'),
    phase: json.str('phase'),
    isNew: json.boolean('is_new'),
  );

  final String id;

  /// The contribution or corrected attempt this card practises.
  final String itemId;
  final DateTime due;
  final String phase;
  final bool isNew;
}

enum PromptKind {
  /// A sentence my partner taught me: read it, recall what it means.
  taught,

  /// My own sentence that my partner corrected: recall the right version.
  corrected,
}

/// One card with the text it shows, put together on the device from data it
/// already has (the API returns only `item_id`).
class ReviewItem {
  const ReviewItem({
    required this.card,
    required this.kind,
    required this.front,
    required this.frontLanguage,
    required this.back,
    required this.backLanguage,
    this.note,
  });

  final ReviewCard card;
  final PromptKind kind;
  final String front;
  final String frontLanguage;
  final String? back;
  final String? backLanguage;
  final String? note;

  /// Matches cards with their contribution or attempt. Cards whose item is
  /// unknown (for example removed later) are left out.
  static List<ReviewItem> resolve(
    List<ReviewCard> cards, {
    required Iterable<Contribution> contributions,
    required Iterable<Attempt> attempts,
  }) {
    final taught = {for (final c in contributions) c.id: c};
    final corrected = {
      for (final a in attempts)
        if (a.correction != null) a.id: a,
    };
    final items = <ReviewItem>[];
    for (final card in cards) {
      final c = taught[card.itemId];
      final a = corrected[card.itemId];
      if (c != null) {
        items.add(
          ReviewItem(
            card: card,
            kind: PromptKind.taught,
            front: c.text,
            frontLanguage: c.language,
            back: c.gloss,
            backLanguage: c.glossLanguage,
            note: c.note,
          ),
        );
      } else if (a != null) {
        items.add(
          ReviewItem(
            card: card,
            kind: PromptKind.corrected,
            front: a.text,
            frontLanguage: a.language,
            back: a.correction!.correctedText,
            backLanguage: a.language,
            note: a.correction!.comment,
          ),
        );
      }
    }
    return items;
  }
}
