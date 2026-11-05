import '../../../core/json.dart';

class Member {
  const Member({
    required this.userId,
    required this.teaches,
    required this.learns,
  });

  factory Member.fromJson(Json json) => Member(
    userId: json.str('user_id'),
    teaches: json.str('teaches'),
    learns: json.str('learns'),
  );

  final String userId;
  final String teaches;
  final String learns;
}

class Pair {
  const Pair({
    required this.id,
    required this.createdAt,
    required this.members,
  });

  factory Pair.fromJson(Json json) => Pair(
    id: json.str('id'),
    createdAt: json.time('created_at'),
    members: json.objects('members').map(Member.fromJson).toList(),
  );

  final String id;
  final DateTime createdAt;
  final List<Member> members;

  Member me(String accountId) =>
      members.firstWhere((m) => m.userId == accountId);

  Member partnerOf(String accountId) =>
      members.firstWhere((m) => m.userId != accountId);
}

class Contribution {
  const Contribution({
    required this.id,
    required this.pairId,
    required this.authorId,
    required this.learnerId,
    required this.language,
    required this.text,
    required this.createdAt,
    this.gloss,
    this.glossLanguage,
    this.note,
  });

  factory Contribution.fromJson(Json json) => Contribution(
    id: json.str('id'),
    pairId: json.str('pair_id'),
    authorId: json.str('author_id'),
    learnerId: json.str('learner_id'),
    language: json.str('language'),
    text: json.str('text'),
    createdAt: json.time('created_at'),
    gloss: json.strOrNull('gloss'),
    glossLanguage: json.strOrNull('gloss_language'),
    note: json.strOrNull('note'),
  );

  final String id;
  final String pairId;
  final String authorId;
  final String learnerId;
  final String language;
  final String text;
  final DateTime createdAt;
  final String? gloss;
  final String? glossLanguage;
  final String? note;
}

class Correction {
  const Correction({
    required this.correctedText,
    required this.correctedAt,
    this.comment,
  });

  factory Correction.fromJson(Json json) => Correction(
    correctedText: json.str('corrected_text'),
    comment: json.strOrNull('comment'),
    correctedAt: json.time('corrected_at'),
  );

  final String correctedText;
  final String? comment;
  final DateTime correctedAt;
}

class Attempt {
  const Attempt({
    required this.id,
    required this.pairId,
    required this.learnerId,
    required this.reviewerId,
    required this.language,
    required this.text,
    required this.createdAt,
    this.correction,
  });

  factory Attempt.fromJson(Json json) {
    final correction = json.objOrNull('correction');
    return Attempt(
      id: json.str('id'),
      pairId: json.str('pair_id'),
      learnerId: json.str('learner_id'),
      reviewerId: json.str('reviewer_id'),
      language: json.str('language'),
      text: json.str('text'),
      createdAt: json.time('created_at'),
      correction: correction == null ? null : Correction.fromJson(correction),
    );
  }

  final String id;
  final String pairId;
  final String learnerId;
  final String reviewerId;
  final String language;
  final String text;
  final DateTime createdAt;
  final Correction? correction;
}

class Invitation {
  const Invitation({required this.code, required this.expiresInDays});

  factory Invitation.fromJson(Json json) => Invitation(
    code: json.str('code'),
    expiresInDays: json.integer('expires_in_days'),
  );

  final String code;
  final int expiresInDays;
}
