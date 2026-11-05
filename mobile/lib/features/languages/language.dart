import 'package:flutter/widgets.dart' show TextDirection;

import '../../core/api/api_client.dart';
import '../../core/json.dart';

class Language {
  const Language({
    required this.code,
    required this.englishName,
    required this.nativeName,
    required this.direction,
  });

  factory Language.fromJson(Json json) => Language(
    code: json.str('code'),
    englishName: json.str('english_name'),
    nativeName: json.str('native_name'),
    direction: json.str('direction') == 'rtl'
        ? TextDirection.rtl
        : TextDirection.ltr,
  );

  final String code;
  final String englishName;
  final String nativeName;
  final TextDirection direction;
}

class LanguagesApi {
  LanguagesApi(this._client);
  final ApiClient _client;

  /// Every language the server knows, by ISO code.
  Future<Map<String, Language>> all() async {
    final list = asJsonList(await _client.get('/v1/languages'));
    return {for (final l in list.map(Language.fromJson)) l.code: l};
  }
}
