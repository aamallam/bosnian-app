import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../auth/session.dart';
import 'api_exception.dart';

/// JSON over HTTPS to the Langex API. Adds the access token, refreshes it
/// once after a 401 and turns error answers into [ApiException]s.
class ApiClient {
  ApiClient({
    required this._baseUrl,
    required http.Client client,
    this._session,
    this.timeout = const Duration(seconds: 20),
  }) : _http = client;

  final Uri _baseUrl;
  final http.Client _http;
  final Session? _session;
  final Duration timeout;

  Future<Object?> get(String path, {Map<String, String>? query}) =>
      _send('GET', path, query: query);

  Future<Object?> post(String path, {Object? body}) =>
      _send('POST', path, body: body);

  Future<Object?> _send(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
  }) async {
    final session = _session;
    var token = session == null ? null : await session.accessToken();
    if (session != null && token == null) {
      throw const ApiException(ApiErrorKind.unauthorized);
    }
    var response = await _request(method, path, query, body, token);
    if (response.statusCode == 401 && session != null && token != null) {
      token = await session.refreshAfterRejection(token);
      if (token == null) throw ApiException.fromStatus(401);
      response = await _request(method, path, query, body, token);
      if (response.statusCode == 401) {
        await session.end();
      }
    }
    return _decode(response);
  }

  Future<http.Response> _request(
    String method,
    String path,
    Map<String, String>? query,
    Object? body,
    String? token,
  ) async {
    final uri = _baseUrl.replace(
      path: '${_baseUrl.path.replaceAll(RegExp(r'/$'), '')}$path',
      queryParameters: (query == null || query.isEmpty) ? null : query,
    );
    final request = http.Request(method, uri)
      ..headers['Accept'] = 'application/json'
      ..followRedirects = false; // never send the token somewhere else
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    try {
      final streamed = await _http.send(request).timeout(timeout);
      return await http.Response.fromStream(streamed).timeout(timeout);
    } on TimeoutException {
      throw const ApiException(ApiErrorKind.network);
    } on http.ClientException {
      throw const ApiException(ApiErrorKind.network);
    }
  }

  Object? _decode(http.Response response) {
    final status = response.statusCode;
    if (status >= 200 && status < 300) {
      if (response.bodyBytes.isEmpty) return null;
      try {
        return jsonDecode(utf8.decode(response.bodyBytes));
      } on FormatException {
        throw ApiException(ApiErrorKind.network, status: status);
      }
    }
    String? title;
    try {
      final problem = jsonDecode(utf8.decode(response.bodyBytes));
      if (problem is Map<String, Object?> && problem['title'] is String) {
        title = problem['title']! as String;
      }
    } on FormatException {
      // not problem+json (for example a proxy error page)
    }
    final retryAfter = int.tryParse(response.headers['retry-after'] ?? '');
    throw ApiException.fromStatus(
      status,
      title: title,
      retryAfter: retryAfter == null ? null : Duration(seconds: retryAfter),
    );
  }
}
