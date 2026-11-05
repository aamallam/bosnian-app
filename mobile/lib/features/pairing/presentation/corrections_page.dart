import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/ui/async_view.dart';
import '../../../core/ui/forms.dart';
import '../../../l10n/app_localizations.dart';
import '../../languages/languages_provider.dart';
import '../application/pairing_providers.dart';
import '../domain/models.dart';

/// Sentences my partners wrote in my language, waiting for my correction.
class CorrectionsPage extends ConsumerWidget {
  const CorrectionsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final waiting = ref.watch(toReviewProvider);
    final languages = ref.watch(languagesProvider).value ?? const {};
    return Scaffold(
      appBar: AppBar(title: Text(l.correctionsTitle)),
      body: AsyncView(
        value: waiting,
        onRetry: () => ref.invalidate(toReviewProvider),
        builder: (attempts) => attempts.isEmpty
            ? Center(child: Text(l.nothingToCorrect))
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final a in attempts)
                    Card(
                      child: ListTile(
                        title: LangText(
                          a.text,
                          direction: languages.directionOf(a.language),
                        ),
                        trailing: const Icon(Icons.edit_outlined),
                        onTap: () => showModalBottomSheet<void>(
                          context: context,
                          isScrollControlled: true,
                          builder: (_) => _CorrectionSheet(attempt: a),
                        ),
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}

class _CorrectionSheet extends ConsumerStatefulWidget {
  const _CorrectionSheet({required this.attempt});
  final Attempt attempt;

  @override
  ConsumerState<_CorrectionSheet> createState() => _CorrectionSheetState();
}

class _CorrectionSheetState extends ConsumerState<_CorrectionSheet> {
  final _form = GlobalKey<FormState>();
  late final _text = TextEditingController(text: widget.attempt.text);
  final _comment = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _text.dispose();
    _comment.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(pairingApiProvider)
          .correct(
            widget.attempt.id,
            correctedText: _text.text.trim(),
            comment: optional(_comment),
          );
      ref.invalidate(toReviewProvider);
      if (mounted) Navigator.of(context).pop();
    } on Exception catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final languages = ref.watch(languagesProvider).value ?? const {};
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.viewInsetsOf(context).bottom + 16,
      ),
      child: Form(
        key: _form,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LangText(
              widget.attempt.text,
              direction: languages.directionOf(widget.attempt.language),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            TextFormField(
              key: const Key('corrected'),
              controller: _text,
              textDirection: languages.directionOf(widget.attempt.language),
              maxLines: null,
              decoration: InputDecoration(labelText: l.correctedLabel),
              validator: (v) => validateText(v, l),
            ),
            TextFormField(
              key: const Key('comment'),
              controller: _comment,
              maxLines: null,
              decoration: InputDecoration(labelText: l.commentLabel),
              validator: (v) =>
                  validateText(v, l, required: false, max: maxNoteLength),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _busy ? null : _send,
              child: Text(l.sendCorrection),
            ),
          ],
        ),
      ),
    );
  }
}
