import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import 'language.dart';

/// Loaded once per app run; the list changes only with a server release.
final languagesProvider = FutureProvider<Map<String, Language>>(
  (ref) => ref.watch(languagesApiProvider).all(),
);

extension LanguageLookup on Map<String, Language> {
  String nameOf(String code) => this[code]?.nativeName ?? code;

  TextDirection directionOf(String code) =>
      this[code]?.direction ?? TextDirection.ltr;
}
