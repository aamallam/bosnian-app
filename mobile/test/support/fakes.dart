import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langex/app/app.dart';
import 'package:langex/app/providers.dart';
import 'package:langex/core/auth/token_store.dart';
import 'package:langex/core/config.dart';
import 'package:langex/features/auth/data/auth_api.dart';
import 'package:langex/features/auth/data/identity_providers.dart';

final apiBase = Uri.parse('https://api.test');

const me = '00000000-0000-4000-8000-000000000001';
const partner = '00000000-0000-4000-8000-000000000002';
const pairId = '00000000-0000-4000-8000-0000000000aa';

Tokens signedIn({DateTime? expires}) => Tokens(
  accessToken: 'access-1',
  refreshToken: 'refresh-1',
  accessExpiresAt:
      expires ?? DateTime.now().toUtc().add(const Duration(minutes: 15)),
  accountId: me,
);

/// A scripted API: answers by "METHOD /path" and records every request.
class FakeBackend {
  final _routes = <String, http.Response Function(http.Request)>{};
  final requests = <http.Request>[];

  void on(String method, String path, Object? body, {int status = 200}) {
    _routes['$method $path'] = (_) => json(body, status: status);
  }

  void onCall(
    String method,
    String path,
    http.Response Function(http.Request) answer,
  ) {
    _routes['$method $path'] = answer;
  }

  static http.Response json(Object? body, {int status = 200}) =>
      http.Response.bytes(
        body == null ? const [] : utf8.encode(jsonEncode(body)),
        status,
        headers: {
          'content-type': status >= 400
              ? 'application/problem+json'
              : 'application/json',
        },
      );

  Iterable<String> get calls =>
      requests.map((r) => '${r.method} ${r.url.path}');

  Map<String, Object?> bodyOf(String call) {
    final request = requests.lastWhere(
      (r) => '${r.method} ${r.url.path}' == call,
    );
    return jsonDecode(request.body) as Map<String, Object?>;
  }

  http.Client get client => MockClient((request) async {
    requests.add(request);
    final answer = _routes['${request.method} ${request.url.path}'];
    if (answer == null) {
      return json({'title': 'Not Found', 'status': 404}, status: 404);
    }
    return answer(request);
  });
}

/// The usual data of a signed-in user with one partner.
void seedPair(FakeBackend api, {int streak = 2}) {
  api
    ..on('GET', '/v1/languages', [
      {
        'code': 'bs',
        'english_name': 'Bosnian',
        'native_name': 'bosanski',
        'direction': 'ltr',
        'scripts': ['Latn'],
      },
      {
        'code': 'ar',
        'english_name': 'Arabic',
        'native_name': 'العربية',
        'direction': 'rtl',
        'scripts': ['Arab'],
      },
    ])
    ..on('GET', '/v1/pairs', [
      {
        'id': pairId,
        'created_at': '2026-11-01T10:00:00Z',
        'members': [
          {'user_id': me, 'teaches': 'bs', 'learns': 'ar'},
          {'user_id': partner, 'teaches': 'ar', 'learns': 'bs'},
        ],
      },
    ])
    ..on('GET', '/v1/pairs/$pairId/streak', {'days': streak})
    ..on('GET', '/v1/attempts/to-review', <Object>[])
    ..on('GET', '/v1/reviews/session', <Object>[]);
}

Future<ProviderContainer> pumpApp(
  WidgetTester tester,
  FakeBackend api, {
  Tokens? tokens,
  bool devSignIn = true,
  List<IdentityProvider> identity = const [],
}) async {
  final container = ProviderContainer(
    overrides: [
      configProvider.overrideWithValue(
        AppConfig(apiBaseUrl: apiBase, devSignIn: devSignIn),
      ),
      httpClientProvider.overrideWithValue(api.client),
      tokenStoreProvider.overrideWithValue(MemoryTokenStore(tokens)),
      identityProvidersProvider.overrideWithValue(identity),
    ],
    retry: (_, _) => null,
  );
  addTearDown(container.dispose);
  await container.read(sessionProvider).restore();
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const LangexApp()),
  );
  await tester.pumpAndSettle();
  return container;
}

/// Finds text in whichever language the test runs.
Finder textOf(String text) => find.text(text, findRichText: true);

extension Settle on WidgetTester {
  Future<void> tapAndSettle(Finder finder) async {
    await ensureVisible(finder);
    await tap(finder);
    await pumpAndSettle();
  }
}

Widget wrap(Widget child) => MaterialApp(home: child);

/// A Google stand-in: returns an ID token that names the nonce it was given,
/// or null (cancelled), or throws.
class FakeIdentityProvider implements IdentityProvider {
  FakeIdentityProvider({this.id = 'google', this.result = 'ok'});

  @override
  final String id;

  /// 'ok', 'cancel' or 'fail'.
  String result;
  final nonces = <String>[];
  int forgotten = 0;

  @override
  Future<SignInCredential?> obtain(String nonce) async {
    nonces.add(nonce);
    return switch (result) {
      'cancel' => null,
      'fail' => throw const SignInFailed('test'),
      _ => SignInCredential(
        provider: id,
        idToken: '$id-token:$nonce',
        nonce: nonce,
      ),
    };
  }

  @override
  Future<void> forget() async => forgotten++;
}
