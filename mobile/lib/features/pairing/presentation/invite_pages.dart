import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/providers.dart';
import '../../../core/ui/async_view.dart';
import '../../../l10n/app_localizations.dart';
import '../../languages/language.dart';
import '../../languages/languages_provider.dart';
import '../application/pairing_providers.dart';
import '../domain/models.dart';

class InvitePage extends ConsumerStatefulWidget {
  const InvitePage({super.key});

  @override
  ConsumerState<InvitePage> createState() => _InvitePageState();
}

class _InvitePageState extends ConsumerState<InvitePage> {
  String? _teaches;
  String? _learns;
  Invitation? _invitation;
  bool _busy = false;

  Future<void> _create() async {
    setState(() => _busy = true);
    try {
      final invitation = await ref
          .read(pairingApiProvider)
          .invite(teaches: _teaches!, learns: _learns!);
      if (mounted) setState(() => _invitation = invitation);
    } on Exception catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final languages = ref.watch(languagesProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.invitePartner)),
      body: AsyncView(
        value: languages,
        onRetry: () => ref.invalidate(languagesProvider),
        builder: (languages) {
          final invitation = _invitation;
          return invitation == null
              ? _chooser(l, languages.values.toList())
              : _code(l, invitation);
        },
      ),
    );
  }

  Widget _chooser(AppLocalizations l, List<Language> languages) {
    final same = _teaches != null && _teaches == _learns;
    DropdownMenuItem<String> item(Language lang) => DropdownMenuItem(
      value: lang.code,
      child: Text('${lang.nativeName} (${lang.englishName})'),
    );
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        DropdownButtonFormField<String>(
          key: const Key('teaches'),
          initialValue: _teaches,
          decoration: InputDecoration(labelText: l.iTeach),
          items: languages.map(item).toList(),
          onChanged: (v) => setState(() => _teaches = v),
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          key: const Key('learns'),
          initialValue: _learns,
          decoration: InputDecoration(
            labelText: l.iLearn,
            errorText: same ? l.sameLanguage : null,
          ),
          items: languages.map(item).toList(),
          onChanged: (v) => setState(() => _learns = v),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: _busy || _teaches == null || _learns == null || same
              ? null
              : _create,
          child: Text(l.createCode),
        ),
      ],
    );
  }

  Widget _code(AppLocalizations l, Invitation invitation) => ListView(
    padding: const EdgeInsets.all(24),
    children: [
      Text(l.inviteShare(invitation.expiresInDays)),
      const SizedBox(height: 24),
      SelectableText(
        invitation.code,
        key: const Key('invite-code'),
        textAlign: TextAlign.center,
        textDirection: TextDirection.ltr,
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: 24),
      OutlinedButton.icon(
        icon: const Icon(Icons.copy),
        label: Text(l.copy),
        onPressed: () async {
          await Clipboard.setData(ClipboardData(text: invitation.code));
          if (mounted) showMessage(context, l.copied);
        },
      ),
      const SizedBox(height: 8),
      FilledButton(onPressed: () => context.pop(), child: Text(l.done)),
    ],
  );
}

class JoinPage extends ConsumerStatefulWidget {
  const JoinPage({super.key});

  @override
  ConsumerState<JoinPage> createState() => _JoinPageState();
}

class _JoinPageState extends ConsumerState<JoinPage> {
  final _code = TextEditingController();
  final _form = GlobalKey<FormState>();
  bool _busy = false;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _join() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      final pair = await ref.read(pairingApiProvider).accept(_code.text);
      ref.invalidate(pairsProvider);
      if (mounted) context.pushReplacement('/pairs/${pair.id}');
    } on Exception catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.joinWithCode)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            TextFormField(
              key: const Key('join-code'),
              controller: _code,
              textDirection: TextDirection.ltr,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(labelText: l.codeLabel),
              onFieldSubmitted: (_) => _join(),
              validator: (v) {
                final value = v?.trim() ?? '';
                if (value.isEmpty) return l.required;
                if (value.length > 64) return l.tooLong;
                return null;
              },
            ),
            const SizedBox(height: 24),
            FilledButton(onPressed: _busy ? null : _join, child: Text(l.join)),
          ],
        ),
      ),
    );
  }
}
