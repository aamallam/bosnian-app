/// An error answer from the API (RFC 9457 problem details), or a network
/// failure. Screens show [kind]-based messages, never raw server text.
enum ApiErrorKind {
  /// No connection, timeout or an unreadable answer.
  network,

  /// 401: the session ended; the user has to sign in again.
  unauthorized,

  /// 404: missing, or not ours (the API does not tell them apart).
  notFound,

  /// 409: already done, for example an attempt that was corrected already.
  conflict,

  /// 400 or 422: the input was refused, for example a wrong invitation code.
  invalid,

  /// 429: rate limit or the daily sentence limit.
  tooMany,

  /// Anything else, including 5xx.
  server,
}

class ApiException implements Exception {
  const ApiException(this.kind, {this.status, this.title, this.retryAfter});

  factory ApiException.fromStatus(
    int status, {
    String? title,
    Duration? retryAfter,
  }) {
    final kind = switch (status) {
      401 => ApiErrorKind.unauthorized,
      404 => ApiErrorKind.notFound,
      409 => ApiErrorKind.conflict,
      400 || 422 => ApiErrorKind.invalid,
      429 => ApiErrorKind.tooMany,
      _ => ApiErrorKind.server,
    };
    return ApiException(
      kind,
      status: status,
      title: title,
      retryAfter: retryAfter,
    );
  }

  final ApiErrorKind kind;
  final int? status;

  /// The problem `title`, for logs and tests only.
  final String? title;
  final Duration? retryAfter;

  @override
  String toString() => 'ApiException($kind, status: $status, title: $title)';
}
