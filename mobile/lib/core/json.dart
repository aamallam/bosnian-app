/// Strict readers for API answers: a missing or mistyped field fails with a
/// [FormatException] instead of turning into a null somewhere in the UI.
typedef Json = Map<String, Object?>;

extension JsonRead on Json {
  T _get<T>(String key) {
    final value = this[key];
    if (value is T) return value;
    throw FormatException(
      'Field "$key" should be $T, got ${value.runtimeType}',
    );
  }

  String str(String key) => _get<String>(key);
  String? strOrNull(String key) => _get<String?>(key);
  int integer(String key) => _get<int>(key);
  bool boolean(String key) => _get<bool>(key);
  DateTime time(String key) => DateTime.parse(str(key)).toUtc();
  DateTime? timeOrNull(String key) {
    final value = strOrNull(key);
    return value == null ? null : DateTime.parse(value).toUtc();
  }

  Json obj(String key) => _get<Json>(key);
  Json? objOrNull(String key) => _get<Json?>(key);
  List<Json> objects(String key) => _get<List<Object?>>(key).cast<Json>();
  List<String> strings(String key) => _get<List<Object?>>(key).cast<String>();
}

Json asJson(Object? value) {
  if (value is Json) return value;
  throw FormatException('Expected an object, got ${value.runtimeType}');
}

List<Json> asJsonList(Object? value) {
  if (value is List<Object?>) return value.map(asJson).toList();
  throw FormatException('Expected a list, got ${value.runtimeType}');
}
