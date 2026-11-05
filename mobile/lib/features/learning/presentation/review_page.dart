import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/ui/async_view.dart';
import '../../../l10n/app_localizations.dart';
import '../../languages/languages_provider.dart';
import '../application/review_providers.dart' show reviewQueueProvider;
import '../domain/review_card.dart';

/// One card at a time: read the prompt, try to recall, reveal, rate.
class ReviewPage extends ConsumerWidget {
  const ReviewPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final queue = ref.watch(reviewQueueProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.review)),
      body: AsyncView(
        value: queue,
        onRetry: () => ref.invalidate(reviewQueueProvider),
        builder: (items) => _Session(items: items),
      ),
    );
  }
}

class _Session extends ConsumerStatefulWidget {
  const _Session({required this.items});
  final List<ReviewItem> items;

  @override
  ConsumerState<_Session> createState() => _SessionState();
}

class _SessionState extends ConsumerState<_Session> {
  int _index = 0;
  bool _revealed = false;
  bool _busy = false;
  final _watch = Stopwatch()..start();

  Future<void> _rate(ReviewItem item, Rating rating) async {
    setState(() => _busy = true);
    try {
      await ref
          .read(learningApiProvider)
          .review(item.card.id, rating, took: _watch.elapsed);
      if (!mounted) return;
      setState(() {
        _index++;
        _revealed = false;
      });
      _watch.reset();
    } on Exception catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    if (_index >= widget.items.length) {
      return Center(
        child: Text(l.reviewDone, style: theme.textTheme.headlineSmall),
      );
    }
    final item = widget.items[_index];
    final languages = ref.watch(languagesProvider).value ?? const {};
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LinearProgressIndicator(value: _index / widget.items.length),
          const SizedBox(height: 32),
          Text(
            item.kind == PromptKind.taught ? l.recallMeaning : l.recallCorrect,
            style: theme.textTheme.labelLarge,
          ),
          const SizedBox(height: 12),
          LangText(
            item.front,
            key: const Key('front'),
            direction: languages.directionOf(item.frontLanguage),
            style: theme.textTheme.headlineSmall,
          ),
          const SizedBox(height: 24),
          if (_revealed) ...[
            if (item.back != null)
              LangText(
                item.back!,
                key: const Key('back'),
                direction: languages.directionOf(item.backLanguage ?? ''),
                style: theme.textTheme.titleLarge?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
            if (item.note != null) ...[
              const SizedBox(height: 8),
              Text(item.note!, style: theme.textTheme.bodyMedium),
            ],
          ],
          const Spacer(),
          if (!_revealed)
            FilledButton(
              onPressed: () => setState(() => _revealed = true),
              child: Text(l.showAnswer),
            )
          else
            Row(
              children: [
                for (final (rating, label) in [
                  (Rating.again, l.ratingAgain),
                  (Rating.hard, l.ratingHard),
                  (Rating.good, l.ratingGood),
                  (Rating.easy, l.ratingEasy),
                ])
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: OutlinedButton(
                        key: Key('rate-${rating.name}'),
                        onPressed: _busy ? null : () => _rate(item, rating),
                        child: Text(
                          label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
