import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../core/ui/async_view.dart';
import '../../../l10n/app_localizations.dart';
import '../application/auth_actions.dart';
import '../data/auth_api.dart';

class SignInPage extends ConsumerStatefulWidget {
  const SignInPage({super.key});

  @override
  ConsumerState<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends ConsumerState<SignInPage> {
  final _name = TextEditingController();
  final _form = GlobalKey<FormState>();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _devSignIn() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(authActionsProvider)
          .signIn(SignInCredential.dev(_name.text));
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
    final devSignIn = ref.watch(configProvider).devSignIn;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l.appTitle, style: theme.textTheme.displaySmall),
                  const SizedBox(height: 16),
                  Text(l.signInTitle, style: theme.textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(l.signInBody, style: theme.textTheme.bodyLarge),
                  const SizedBox(height: 32),
                  if (devSignIn)
                    Form(
                      key: _form,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextFormField(
                            key: const Key('dev-name'),
                            controller: _name,
                            decoration: InputDecoration(
                              labelText: l.devNameLabel,
                            ),
                            autofillHints: const [AutofillHints.username],
                            textInputAction: TextInputAction.done,
                            onFieldSubmitted: (_) => _devSignIn(),
                            validator: (v) {
                              final value = v?.trim() ?? '';
                              if (value.isEmpty) return l.required;
                              if (value.length > 64) return l.tooLong;
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          FilledButton(
                            onPressed: _busy ? null : _devSignIn,
                            child: Text(l.signIn),
                          ),
                        ],
                      ),
                    )
                  else
                    Text(l.noSignInMethods, textAlign: TextAlign.center),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
