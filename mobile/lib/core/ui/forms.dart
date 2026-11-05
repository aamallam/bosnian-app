import 'package:flutter/widgets.dart';

import '../../l10n/app_localizations.dart';

/// The same limits as the API, checked before sending.
const maxSentenceLength = 600;
const maxNoteLength = 1200;

String? validateText(
  String? value,
  AppLocalizations l, {
  bool required = true,
  int max = maxSentenceLength,
}) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return required ? l.required : null;
  if (text.length > max) return l.tooLong;
  return null;
}

String? optional(TextEditingController c) {
  final text = c.text.trim();
  return text.isEmpty ? null : text;
}
