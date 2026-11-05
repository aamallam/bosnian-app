import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/providers.dart';
import '../../../core/ui/async_view.dart';
import '../../../l10n/app_localizations.dart';
import '../../auth/application/auth_actions.dart';
import '../../languages/languages_provider.dart';
import '../../learning/application/review_providers.dart';
import '../application/pairing_providers.dart';

class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref
      ..invalidate(pairsProvider)
      ..invalidate(dueCountProvider)
      ..invalidate(toReviewProvider);
    await ref.read(pairsProvider.future);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final pairs = ref.watch(pairsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.appTitle),
        actions: [
          IconButton(
            tooltip: l.joinWithCode,
            icon: const Icon(Icons.group_add_outlined),
            onPressed: () => context.push('/join'),
          ),
          PopupMenuButton<void>(
            itemBuilder: (_) => [
              PopupMenuItem(
                onTap: () => ref.read(authActionsProvider).signOut(),
                child: Text(l.signOut),
              ),
            ],
          ),
        ],
      ),
      body: AsyncView(
        value: pairs,
        onRetry: () => _refresh(ref),
        builder: (pairs) => pairs.isEmpty
            ? const _EmptyState()
            : RefreshIndicator(
                onRefresh: () => _refresh(ref),
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    const _TodayCard(),
                    const SizedBox(height: 8),
                    for (final summary in pairs) _PairTile(summary: summary),
                  ],
                ),
              ),
      ),
      floatingActionButton: (pairs.value?.isEmpty ?? true)
          ? null // the empty state has its own buttons
          : FloatingActionButton.extended(
              onPressed: () => context.push('/invite'),
              icon: const Icon(Icons.person_add_alt_1),
              label: Text(l.invitePartner),
            ),
    );
  }
}

class _TodayCard extends ConsumerWidget {
  const _TodayCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final due = ref.watch(dueCountProvider).value ?? 0;
    final toCorrect = ref.watch(toReviewProvider).value?.length ?? 0;
    return Card(
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.style_outlined),
            title: Text(l.review),
            subtitle: due > 0 ? Text(l.reviewDue(due)) : null,
            trailing: const Icon(Icons.chevron_right),
            // Counts change while away: reload them on return.
            onTap: () async {
              await context.push<void>('/review');
              ref.invalidate(dueCountProvider);
            },
          ),
          if (toCorrect > 0)
            ListTile(
              leading: const Icon(Icons.rate_review_outlined),
              title: Text(l.correctionsTitle),
              subtitle: Text(l.correctionsToGive(toCorrect)),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await context.push<void>('/corrections');
                ref.invalidate(toReviewProvider);
              },
            ),
        ],
      ),
    );
  }
}

class _PairTile extends ConsumerWidget {
  const _PairTile({required this.summary});
  final PairSummary summary;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final languages = ref.watch(languagesProvider).value ?? const {};
    final me = summary.pair.me(ref.watch(sessionProvider).accountId!);
    return Card(
      child: ListTile(
        title: Text(
          l.teachesLearns(
            languages.nameOf(me.teaches),
            languages.nameOf(me.learns),
          ),
        ),
        subtitle: summary.streakDays > 0
            ? Text(l.streakDays(summary.streakDays))
            : null,
        leading: const Icon(Icons.people_alt_outlined),
        trailing: const Icon(Icons.chevron_right),
        onTap: () async {
          await context.push<void>('/pairs/${summary.pair.id}');
          ref.invalidate(pairsProvider); // streak may have grown
        },
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(l.emptyPairsTitle, style: theme.textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(l.emptyPairsBody, textAlign: TextAlign.center),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => context.push('/invite'),
              child: Text(l.invitePartner),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => context.push('/join'),
              child: Text(l.joinWithCode),
            ),
          ],
        ),
      ),
    );
  }
}
