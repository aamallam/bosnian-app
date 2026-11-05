import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langex/core/api/api_client.dart';
import 'package:langex/core/api/api_exception.dart';
import 'package:langex/core/auth/session.dart';
import 'package:langex/core/auth/token_store.dart';

import '../support/fakes.dart';

Tokens _fresh(String access) => Tokens(
  accessToken: access,
  refreshToken: 'refresh-$access',
  accessExpiresAt: DateTime.now().toUtc().add(const Duration(minutes: 15)),
  accountId: me,
);

void main() {
  test('sends the bearer token and decodes JSON', () async {
    final api = FakeBackend()..on('GET', '/v1/me', {'id': me});
    final session = Session(
      MemoryTokenStore(signedIn()),
      (_) async => _fresh('x'),
    );
    await session.restore();
    final client = ApiClient(
      baseUrl: apiBase,
      client: api.client,
      session: session,
    );

    expect(await client.get('/v1/me'), {'id': me});
    final request = api.requests.single;
    expect(request.headers['Authorization'], 'Bearer access-1');
    expect(request.followRedirects, isFalse);
  });

  test('keeps a base path and adds the query', () async {
    final api = FakeBackend()..on('GET', '/api/v1/x', <Object>[]);
    final client = ApiClient(
      baseUrl: Uri.parse('https://h.test/api/'),
      client: api.client,
    );

    await client.get('/v1/x', query: {'since': '2026-01-01T00:00:00.000Z'});

    expect(
      api.requests.single.url.toString(),
      'https://h.test/api/v1/x?since=2026-01-01T00%3A00%3A00.000Z',
    );
  });

  test(
    'turns problem+json into ApiException without server text in the UI',
    () async {
      final api = FakeBackend()
        ..onCall(
          'POST',
          '/v1/pairs/p/contributions',
          (_) => http.Response(
            '{"title":"Daily limit reached","status":429}',
            429,
            headers: {
              'content-type': 'application/problem+json',
              'retry-after': '30',
            },
          ),
        );
      final client = ApiClient(baseUrl: apiBase, client: api.client);

      final error = await client
          .post('/v1/pairs/p/contributions', body: {})
          .then<Object?>((_) => null, onError: (Object e) => e);

      expect(error, isA<ApiException>());
      final e = error! as ApiException;
      expect(e.kind, ApiErrorKind.tooMany);
      expect(e.title, 'Daily limit reached');
      expect(e.retryAfter, const Duration(seconds: 30));
    },
  );

  test('maps status codes to kinds', () {
    expect(ApiException.fromStatus(401).kind, ApiErrorKind.unauthorized);
    expect(ApiException.fromStatus(404).kind, ApiErrorKind.notFound);
    expect(ApiException.fromStatus(409).kind, ApiErrorKind.conflict);
    expect(ApiException.fromStatus(400).kind, ApiErrorKind.invalid);
    expect(ApiException.fromStatus(422).kind, ApiErrorKind.invalid);
    expect(ApiException.fromStatus(503).kind, ApiErrorKind.server);
  });

  test('network failures and timeouts become network errors', () async {
    final failing = ApiClient(
      baseUrl: apiBase,
      client: MockClient((_) => throw http.ClientException('offline')),
    );
    await expectLater(
      failing.get('/v1/languages'),
      throwsA(
        isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.network),
      ),
    );

    final slow = ApiClient(
      baseUrl: apiBase,
      client: MockClient((_) => Completer<http.Response>().future),
      timeout: const Duration(milliseconds: 10),
    );
    await expectLater(
      slow.get('/v1/languages'),
      throwsA(
        isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.network),
      ),
    );
  });

  test('an unreadable success answer is an error, not a crash', () async {
    final client = ApiClient(
      baseUrl: apiBase,
      client: MockClient((_) async => http.Response('<html>', 200)),
    );
    await expectLater(
      client.get('/v1/languages'),
      throwsA(isA<ApiException>()),
    );
  });

  test('without a session, protected calls fail before sending', () async {
    final api = FakeBackend();
    final session = Session(MemoryTokenStore(), (_) async => _fresh('x'));
    await session.restore();
    final client = ApiClient(
      baseUrl: apiBase,
      client: api.client,
      session: session,
    );

    await expectLater(
      client.get('/v1/pairs'),
      throwsA(
        isA<ApiException>().having(
          (e) => e.kind,
          'kind',
          ApiErrorKind.unauthorized,
        ),
      ),
    );
    expect(api.requests, isEmpty);
  });

  group('after a 401', () {
    test('refreshes once and retries', () async {
      final api = FakeBackend()
        ..onCall(
          'GET',
          '/v1/pairs',
          (r) => r.headers['Authorization'] == 'Bearer new'
              ? FakeBackend.json(<Object>[])
              : FakeBackend.json({
                  'title': 'Authentication failed',
                }, status: 401),
        );
      var refreshes = 0;
      final session = Session(MemoryTokenStore(signedIn()), (token) async {
        refreshes++;
        expect(token, 'refresh-1');
        return _fresh('new');
      });
      await session.restore();
      final client = ApiClient(
        baseUrl: apiBase,
        client: api.client,
        session: session,
      );

      // Two requests at once must share one refresh: spending the refresh
      // token twice looks like theft to the server.
      await Future.wait([client.get('/v1/pairs'), client.get('/v1/pairs')]);

      expect(refreshes, 1);
      expect(session.status, SessionStatus.signedIn);
    });

    test('a refused refresh signs the device out', () async {
      final api = FakeBackend()
        ..on('GET', '/v1/pairs', {'title': 'x'}, status: 401);
      final store = MemoryTokenStore(signedIn());
      final session = Session(
        store,
        (_) async => throw ApiException.fromStatus(401),
      );
      await session.restore();
      final client = ApiClient(
        baseUrl: apiBase,
        client: api.client,
        session: session,
      );

      await expectLater(client.get('/v1/pairs'), throwsA(isA<ApiException>()));

      expect(session.status, SessionStatus.signedOut);
      expect(await store.read(), isNull);
    });

    test('offline during refresh keeps the session', () async {
      final api = FakeBackend()
        ..on('GET', '/v1/pairs', {'title': 'x'}, status: 401);
      final session = Session(
        MemoryTokenStore(signedIn()),
        (_) async => throw const ApiException(ApiErrorKind.network),
      );
      await session.restore();
      final client = ApiClient(
        baseUrl: apiBase,
        client: api.client,
        session: session,
      );

      await expectLater(
        client.get('/v1/pairs'),
        throwsA(
          isA<ApiException>().having(
            (e) => e.kind,
            'kind',
            ApiErrorKind.network,
          ),
        ),
      );
      expect(session.status, SessionStatus.signedIn);
    });

    test('a second 401 after a good refresh signs out', () async {
      final api = FakeBackend()
        ..on('GET', '/v1/pairs', {'title': 'x'}, status: 401);
      final session = Session(
        MemoryTokenStore(signedIn()),
        (_) async => _fresh('new'),
      );
      await session.restore();
      final client = ApiClient(
        baseUrl: apiBase,
        client: api.client,
        session: session,
      );

      await expectLater(client.get('/v1/pairs'), throwsA(isA<ApiException>()));
      expect(session.status, SessionStatus.signedOut);
    });
  });

  test('refreshes ahead of expiry instead of failing first', () async {
    final api = FakeBackend()..on('GET', '/v1/me', {'id': me});
    final session = Session(
      MemoryTokenStore(
        signedIn(
          expires: DateTime.now().toUtc().add(const Duration(seconds: 5)),
        ),
      ),
      (_) async => _fresh('early'),
    );
    await session.restore();
    final client = ApiClient(
      baseUrl: apiBase,
      client: api.client,
      session: session,
    );

    await client.get('/v1/me');

    expect(api.requests.single.headers['Authorization'], 'Bearer early');
  });
}
