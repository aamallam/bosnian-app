import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/api/api_exception.dart';
import '../domain/models.dart';

class PairSummary {
  const PairSummary({required this.pair, required this.streakDays});
  final Pair pair;
  final int streakDays;
}

final pairsProvider = FutureProvider.autoDispose<List<PairSummary>>((
  ref,
) async {
  final api = ref.watch(pairingApiProvider);
  final pairs = await api.pairs();
  final streaks = await Future.wait(pairs.map((p) => api.streak(p.id)));
  return [
    for (var i = 0; i < pairs.length; i++)
      PairSummary(pair: pairs[i], streakDays: streaks[i]),
  ];
});

final pairProvider = FutureProvider.autoDispose.family<Pair, String>((
  ref,
  pairId,
) async {
  final pairs = await ref.watch(pairingApiProvider).pairs();
  return pairs.firstWhere(
    (p) => p.id == pairId,
    orElse: () => throw const ApiException(ApiErrorKind.notFound),
  );
});

final contributionsProvider = FutureProvider.autoDispose
    .family<List<Contribution>, String>(
      (ref, pairId) => ref.watch(pairingApiProvider).contributions(pairId),
    );

final myAttemptsProvider = FutureProvider.autoDispose
    .family<List<Attempt>, String>(
      (ref, pairId) => ref.watch(pairingApiProvider).myAttempts(pairId),
    );

final toReviewProvider = FutureProvider.autoDispose<List<Attempt>>(
  (ref) => ref.watch(pairingApiProvider).toReview(),
);
