import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/app_localizations.dart';
import '../api/api_exception.dart';

/// A message the user can act on. Server text is never shown as is.
String errorMessage(Object error, AppLocalizations l) {
  final kind = error is ApiException ? error.kind : ApiErrorKind.server;
  return switch (kind) {
    ApiErrorKind.network => l.errorNetwork,
    ApiErrorKind.unauthorized => l.errorSession,
    ApiErrorKind.notFound => l.errorNotFound,
    ApiErrorKind.conflict => l.errorConflict,
    ApiErrorKind.invalid => l.errorInvalid,
    ApiErrorKind.tooMany => l.errorTooMany,
    ApiErrorKind.server => l.errorServer,
  };
}

void showError(BuildContext context, Object error) {
  final l = AppLocalizations.of(context);
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(errorMessage(error, l))));
}

void showMessage(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}

/// Loading spinner, an error with a retry button, or the content.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
  });

  final AsyncValue<T> value;
  final VoidCallback onRetry;
  final Widget Function(T data) builder;

  @override
  Widget build(BuildContext context) => switch (value) {
    AsyncData(:final value) => builder(value),
    AsyncError(:final error) => ErrorPanel(error: error, onRetry: onRetry),
    _ => const Center(child: CircularProgressIndicator()),
  };
}

class ErrorPanel extends StatelessWidget {
  const ErrorPanel({super.key, required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(errorMessage(error, l), textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: Text(l.retry)),
          ],
        ),
      ),
    );
  }
}

/// Text in a given language, laid out in that language's direction (Arabic
/// stays right-to-left inside an English screen and the other way round).
class LangText extends StatelessWidget {
  const LangText(this.text, {super.key, required this.direction, this.style});
  final String text;
  final TextDirection direction;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) => Text(
    text,
    textDirection: direction,
    textAlign: TextAlign.start,
    style: style,
  );
}
