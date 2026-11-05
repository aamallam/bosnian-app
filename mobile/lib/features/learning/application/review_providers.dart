import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../domain/review_card.dart';

/// Today's cards with their text. The texts come from the sentences and
/// corrections of every pair the user is in.
final reviewQueueProvider = FutureProvider.autoDispose<List<ReviewItem>>((
  ref,
) async {
  final cards = await ref.watch(learningApiProvider).session();
  if (cards.isEmpty) return const [];
  final pairing = ref.watch(pairingApiProvider);
  final pairs = await pairing.pairs();
  final contributions = await Future.wait(
    pairs.map((p) => pairing.contributions(p.id)),
  );
  final attempts = await Future.wait(
    pairs.map((p) => pairing.myAttempts(p.id)),
  );
  return ReviewItem.resolve(
    cards,
    contributions: contributions.expand((c) => c),
    attempts: attempts.expand((a) => a),
  );
});

/// Just the number, for the home screen.
final dueCountProvider = FutureProvider.autoDispose<int>(
  (ref) async => (await ref.watch(learningApiProvider).session()).length,
);
