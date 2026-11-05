import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/ui/async_view.dart';
import '../../../core/ui/forms.dart';
import '../../../l10n/app_localizations.dart';
import '../../languages/language.dart';
import '../../languages/languages_provider.dart';
import '../../learning/application/review_providers.dart';
import '../application/pairing_providers.dart';
import '../domain/models.dart';

class PairPage extends ConsumerWidget {
  const PairPage({super.key, required this.pairId});
  final String pairId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final pair = ref.watch(pairProvider(pairId));
    final languages = ref.watch(languagesProvider).value ?? const {};
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l.appTitle),
          bottom: TabBar(
            tabs: [
              Tab(text: l.tabTeach),
              Tab(text: l.tabPractise),
            ],
          ),
        ),
        body: AsyncView(
          value: pair,
          onRetry: () => ref.invalidate(pairProvider(pairId)),
          builder: (pair) {
            final me = pair.me(ref.watch(sessionProvider).accountId!);
            return TabBarView(
              children: [
                _TeachTab(pair: pair, me: me, languages: languages),
                _PractiseTab(pair: pair, me: me, languages: languages),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _TeachTab extends ConsumerStatefulWidget {
  const _TeachTab({
    required this.pair,
    required this.me,
    required this.languages,
  });
  final Pair pair;
  final Member me;
  final Map<String, Language> languages;

  @override
  ConsumerState<_TeachTab> createState() => _TeachTabState();
}

class _TeachTabState extends ConsumerState<_TeachTab> {
  final _form = GlobalKey<FormState>();
  final _text = TextEditingController();
  final _gloss = TextEditingController();
  final _note = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _text.dispose();
    _gloss.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    if (!_form.currentState!.validate()) return;
    final l = AppLocalizations.of(context);
    setState(() => _busy = true);
    try {
      await ref
          .read(pairingApiProvider)
          .contribute(
            widget.pair.id,
            text: _text.text.trim(),
            gloss: optional(_gloss),
            // The meaning is written in the language my partner speaks.
            glossLanguage: widget.me.learns,
            note: optional(_note),
          );
      _text.clear();
      _gloss.clear();
      _note.clear();
      ref
        ..invalidate(contributionsProvider(widget.pair.id))
        ..invalidate(pairsProvider);
      if (mounted) showMessage(context, l.added);
    } on Exception catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final langs = widget.languages;
    final teaches = widget.me.teaches;
    final explains = widget.me.learns;
    final contributions = ref.watch(contributionsProvider(widget.pair.id));
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Form(
          key: _form,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                key: const Key('sentence'),
                controller: _text,
                textDirection: langs.directionOf(teaches),
                maxLines: null,
                decoration: InputDecoration(
                  labelText: l.sentenceLabel(langs.nameOf(teaches)),
                ),
                validator: (v) => validateText(v, l),
              ),
              TextFormField(
                key: const Key('gloss'),
                controller: _gloss,
                textDirection: langs.directionOf(explains),
                maxLines: null,
                decoration: InputDecoration(
                  labelText: l.glossLabel(langs.nameOf(explains)),
                ),
                validator: (v) => validateText(v, l, required: false),
              ),
              TextFormField(
                key: const Key('note'),
                controller: _note,
                maxLines: null,
                decoration: InputDecoration(labelText: l.noteLabel),
                validator: (v) =>
                    validateText(v, l, required: false, max: maxNoteLength),
              ),
              const SizedBox(height: 12),
              FilledButton(onPressed: _busy ? null : _add, child: Text(l.add)),
            ],
          ),
        ),
        const SizedBox(height: 24),
        AsyncView(
          value: contributions,
          onRetry: () => ref.invalidate(contributionsProvider(widget.pair.id)),
          builder: (items) => items.isEmpty
              ? Text(l.noSentencesYet, textAlign: TextAlign.center)
              : Column(
                  children: [
                    for (final c in items.reversed)
                      Card(
                        child: ListTile(
                          title: LangText(
                            c.text,
                            direction: langs.directionOf(c.language),
                          ),
                          subtitle: c.gloss == null
                              ? null
                              : LangText(
                                  c.gloss!,
                                  direction: langs.directionOf(
                                    c.glossLanguage ?? '',
                                  ),
                                ),
                          trailing: Text(
                            c.authorId == widget.me.userId
                                ? l.fromYou
                                : l.fromPartner,
                            style: Theme.of(context).textTheme.labelSmall,
                          ),
                        ),
                      ),
                  ],
                ),
        ),
      ],
    );
  }
}

class _PractiseTab extends ConsumerStatefulWidget {
  const _PractiseTab({
    required this.pair,
    required this.me,
    required this.languages,
  });
  final Pair pair;
  final Member me;
  final Map<String, Language> languages;

  @override
  ConsumerState<_PractiseTab> createState() => _PractiseTabState();
}

class _PractiseTabState extends ConsumerState<_PractiseTab> {
  final _form = GlobalKey<FormState>();
  final _text = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (!_form.currentState!.validate()) return;
    final l = AppLocalizations.of(context);
    setState(() => _busy = true);
    try {
      await ref
          .read(pairingApiProvider)
          .submitAttempt(widget.pair.id, _text.text.trim());
      _text.clear();
      ref
        ..invalidate(myAttemptsProvider(widget.pair.id))
        ..invalidate(reviewQueueProvider);
      if (mounted) showMessage(context, l.sent);
    } on Exception catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final langs = widget.languages;
    final learns = widget.me.learns;
    final dir = langs.directionOf(learns);
    final attempts = ref.watch(myAttemptsProvider(widget.pair.id));
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Form(
          key: _form,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                key: const Key('attempt'),
                controller: _text,
                textDirection: dir,
                maxLines: null,
                decoration: InputDecoration(
                  labelText: l.practiseLabel(langs.nameOf(learns)),
                ),
                validator: (v) => validateText(v, l),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _busy ? null : _send,
                child: Text(l.send),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        AsyncView(
          value: attempts,
          onRetry: () => ref.invalidate(myAttemptsProvider(widget.pair.id)),
          builder: (items) => Column(
            children: [
              for (final a in items.reversed)
                Card(
                  child: ListTile(
                    title: LangText(
                      a.text,
                      direction: dir,
                      style:
                          a.correction == null ||
                              a.correction!.correctedText == a.text
                          ? null // waiting, or already perfect
                          : const TextStyle(
                              decoration: TextDecoration.lineThrough,
                            ),
                    ),
                    subtitle: a.correction == null
                        ? Text(l.awaitingCorrection)
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              LangText(
                                a.correction!.correctedText,
                                direction: dir,
                              ),
                              if (a.correction!.comment != null)
                                Text(a.correction!.comment!),
                            ],
                          ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
