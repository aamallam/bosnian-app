import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'app/providers.dart';
import 'core/api/api_exception.dart';
import 'core/config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final container = ProviderContainer(
    overrides: [configProvider.overrideWithValue(AppConfig.fromEnvironment())],
    retry: retryOnlyNetworkErrors,
  );
  unawaited(container.read(sessionProvider).restore());
  runApp(
    UncontrolledProviderScope(container: container, child: const LangexApp()),
  );
}

/// Riverpod retries failed providers by default. Only a lost connection is
/// worth retrying; a 4xx answer will not change by asking again.
Duration? retryOnlyNetworkErrors(int retryCount, Object error) {
  if (retryCount >= 3) return null;
  if (error is ApiException && error.kind == ApiErrorKind.network) {
    return Duration(seconds: 1 << retryCount);
  }
  return null;
}
