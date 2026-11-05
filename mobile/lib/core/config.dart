/// Build-time settings, passed with `--dart-define` (never secrets: anything
/// in the app binary is public).
///
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
///               --dart-define=DEV_SIGN_IN=true
class AppConfig {
  AppConfig({required this.apiBaseUrl, this.devSignIn = false}) {
    if (!apiBaseUrl.hasScheme || apiBaseUrl.host.isEmpty) {
      throw ArgumentError.value(apiBaseUrl, 'apiBaseUrl', 'must be absolute');
    }
    final local = _localHosts.contains(apiBaseUrl.host);
    if (apiBaseUrl.scheme != 'https' &&
        !(apiBaseUrl.scheme == 'http' && local)) {
      throw ArgumentError.value(
        apiBaseUrl,
        'apiBaseUrl',
        'must use https (plain http only for a local development server)',
      );
    }
  }

  factory AppConfig.fromEnvironment() => AppConfig(
    apiBaseUrl: Uri.parse(
      const String.fromEnvironment(
        'API_BASE_URL',
        // The Android emulator reaches the host machine at 10.0.2.2.
        defaultValue: 'http://10.0.2.2:8000',
      ),
    ),
    devSignIn: const bool.fromEnvironment('DEV_SIGN_IN'),
  );

  static const _localHosts = {'localhost', '127.0.0.1', '10.0.2.2'};

  final Uri apiBaseUrl;

  /// Shows the `dev:<name>` sign-in, which only a development server accepts.
  final bool devSignIn;
}
