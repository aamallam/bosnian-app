/// Contract tests: every API call the app makes is checked against the
/// backend's OpenAPI document (`openapi.json`, refreshed from the backend;
/// a backend test fails when it is out of date).
///
/// The fake server below is built from that document only. It refuses
/// unknown routes, request fields the API does not accept (the API forbids
/// unknown fields) and missing required fields, and it answers with data
/// generated from the response schemas, which the app's parsers must read.
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langex/core/api/api_client.dart';
import 'package:langex/core/auth/session.dart';
import 'package:langex/core/auth/token_store.dart';
import 'package:langex/features/auth/data/auth_api.dart';
import 'package:langex/features/languages/language.dart';
import 'package:langex/features/learning/data/learning_api.dart';
import 'package:langex/features/learning/domain/review_card.dart';
import 'package:langex/features/pairing/data/pairing_api.dart';

import '../support/fakes.dart';

typedef Schema = Map<String, Object?>;

class Operation {
  Operation(this.method, this.template, this.spec)
    : pattern = RegExp(
        '^${template.replaceAllMapped(RegExp(r'\{[^}]+\}'), (_) => '[^/]+')}\$',
      );

  final String method;
  final String template;
  final Schema spec;
  final RegExp pattern;

  String get id => '$method $template';
}

class OpenApi {
  OpenApi(this.doc)
    : operations = [
        for (final MapEntry(key: path, value: ops)
            in (doc['paths']! as Schema).entries)
          for (final MapEntry(key: method, value: op)
              in (ops! as Schema).entries)
            Operation(method.toUpperCase(), path, op! as Schema),
      ];

  factory OpenApi.load() => OpenApi(
    jsonDecode(File('test/contract/openapi.json').readAsStringSync()) as Schema,
  );

  final Schema doc;
  final List<Operation> operations;

  Schema resolve(Schema schema) {
    final ref = schema[r'$ref'];
    if (ref is! String) return schema;
    final name = ref.split('/').last;
    return resolve(
      ((doc['components']! as Schema)['schemas']! as Schema)[name]! as Schema,
    );
  }

  /// A schema with `anyOf: [X, null]` (an optional field) becomes X.
  Schema nonNull(Schema schema) {
    final s = resolve(schema);
    final anyOf = s['anyOf'];
    if (anyOf is List) {
      return nonNull(
        anyOf.cast<Schema>().firstWhere((o) => o['type'] != 'null'),
      );
    }
    return s;
  }

  Object? example(Schema schema) {
    final s = nonNull(schema);
    if (s['enum'] case final List<Object?> values) return values.first;
    return switch (s['type']) {
      'object' => {
        for (final MapEntry(:key, :value)
            in ((s['properties'] ?? <String, Object?>{}) as Schema).entries)
          key: example(value! as Schema),
      },
      'array' => [example(s['items']! as Schema)],
      'integer' => 1,
      'number' => 1.5,
      'boolean' => true,
      'string' => switch (s['format']) {
        'uuid' => '00000000-0000-4000-8000-000000000001',
        'date-time' => '2026-11-05T10:00:00Z',
        _ => 'text',
      },
      _ => throw UnsupportedError('No example for $s'),
    };
  }

  /// Problems with a request body, or an empty list when it fits the schema.
  List<String> check(Object? value, Schema schema, String at) {
    final s = nonNull(schema);
    if (s['enum'] case final List<Object?> values) {
      return values.contains(value)
          ? []
          : ['$at: $value is not one of $values'];
    }
    switch (s['type']) {
      case 'object':
        if (value is! Map<String, Object?>) return ['$at: expected an object'];
        final properties = (s['properties'] ?? <String, Object?>{}) as Schema;
        final required = ((s['required'] ?? <Object?>[]) as List)
            .cast<String>();
        return [
          for (final key in value.keys)
            if (!properties.containsKey(key))
              '$at.$key: not accepted by the API',
          for (final key in required)
            if (!value.containsKey(key)) '$at.$key: required by the API',
          for (final MapEntry(:key, value: v) in value.entries)
            if (properties[key] case final Schema p) ...check(v, p, '$at.$key'),
        ];
      case 'string':
        return value is String ? [] : ['$at: expected a string'];
      case 'integer':
        return value is int ? [] : ['$at: expected an integer'];
      default:
        return [];
    }
  }
}

/// Answers like the real API would, judging only by the document.
class ContractServer {
  ContractServer(this.api);
  final OpenApi api;
  final used = <String>{};
  final problems = <String>[];

  http.Client get client => MockClient((request) async {
    final matches = api.operations.where(
      (o) => o.method == request.method && o.pattern.hasMatch(request.url.path),
    );
    if (matches.isEmpty) {
      problems.add('${request.method} ${request.url.path}: no such operation');
      return http.Response('', 404);
    }
    final op = matches.first;
    used.add(op.id);

    final query = request.url.queryParameters.keys.toSet();
    final declared = {
      for (final p
          in ((op.spec['parameters'] ?? <Object?>[]) as List).cast<Schema>())
        if (p['in'] == 'query') p['name'],
    };
    for (final name in query.difference(declared)) {
      problems.add('${op.id}: unknown query parameter $name');
    }

    final bodySpec = op.spec['requestBody'] as Schema?;
    if (bodySpec != null) {
      final schema =
          ((bodySpec['content']! as Schema)['application/json']!
                  as Schema)['schema']!
              as Schema;
      problems.addAll(api.check(jsonDecode(request.body), schema, op.id));
    } else if (request.body.isNotEmpty) {
      problems.add('${op.id}: sends a body the API does not take');
    }

    final responses = op.spec['responses']! as Schema;
    final status = responses.keys.firstWhere((k) => k.startsWith('2'));
    final content = (responses[status]! as Schema)['content'] as Schema?;
    final schema =
        (content?['application/json'] as Schema?)?['schema'] as Schema?;
    return FakeBackend.json(
      schema == null || schema.isEmpty ? null : api.example(schema),
      status: int.parse(status),
    );
  });
}

/// Operations the app deliberately does not call, and why.
const notUsedByTheApp = {
  'GET /v1/me', // the account id already comes with every token response
};

void main() {
  final spec = OpenApi.load();

  test('every API call matches the backend contract', () async {
    final server = ContractServer(spec);
    final session = Session(
      MemoryTokenStore(signedIn()),
      (_) async => signedIn(),
    );
    await session.restore();
    final authed = ApiClient(
      baseUrl: apiBase,
      client: server.client,
      session: session,
    );
    final public = ApiClient(baseUrl: apiBase, client: server.client);

    final auth = AuthApi(public);
    await auth.signIn(SignInCredential.dev('amina'));
    await auth.signIn(
      const SignInCredential(provider: 'google', idToken: 't', nonce: 'n'),
    );
    await auth.refresh('r');
    await auth.signOut('r');

    final languages = await LanguagesApi(authed).all();
    expect(languages.values.single.code, isNotEmpty);

    final pairing = PairingApi(authed);
    await pairing.invite(teaches: 'bs', learns: 'ar');
    final pair = await pairing.accept('code');
    expect(pair.members, isNotEmpty);
    await pairing.pairs();
    await pairing.contribute(pair.id, text: 't');
    await pairing.contribute(
      pair.id,
      text: 't',
      gloss: 'g',
      glossLanguage: 'bs',
      note: 'n',
    );
    await pairing.contributions(pair.id);
    await pairing.contributions(pair.id, since: DateTime.utc(2026));
    final attempt = await pairing.submitAttempt(pair.id, 't');
    expect(attempt.correction, isNotNull); // example data fills optional fields
    await pairing.myAttempts(pair.id);
    expect(await pairing.streak(pair.id), 1);
    await pairing.toReview();
    await pairing.correct(attempt.id, correctedText: 't');
    await pairing.correct(attempt.id, correctedText: 't', comment: 'c');

    final learning = LearningApi(authed);
    final cards = await learning.session();
    await learning.review(
      cards.single.id,
      Rating.good,
      took: const Duration(seconds: 2),
    );
    await learning.review(cards.single.id, Rating.again);

    expect(server.problems, isEmpty);
    // The client covers the whole API: a new endpoint needs a client call
    // (or an explicit decision to leave it out).
    expect(
      spec.operations
          .map((o) => o.id)
          .toSet()
          .difference(server.used)
          .difference(notUsedByTheApp),
      isEmpty,
    );
  });

  test('the checker itself catches drift', () {
    final schema = {r'$ref': '#/components/schemas/ContributionIn'};
    expect(spec.check({'text': 't'}, schema, 'body'), isEmpty);
    expect(spec.check({'txt': 't'}, schema, 'body'), hasLength(2));
    expect(spec.check({'text': 1}, schema, 'body'), hasLength(1));
    expect(
      spec.check(
        {'provider': 'facebook', 'id_token': 't'},
        {r'$ref': '#/components/schemas/SignInRequest'},
        'b',
      ),
      hasLength(1),
    );
  });
}
