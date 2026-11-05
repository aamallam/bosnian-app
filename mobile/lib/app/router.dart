import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/session.dart';
import '../features/auth/presentation/sign_in_page.dart';
import '../features/learning/presentation/review_page.dart';
import '../features/pairing/presentation/corrections_page.dart';
import '../features/pairing/presentation/home_page.dart';
import '../features/pairing/presentation/invite_pages.dart';
import '../features/pairing/presentation/pair_page.dart';
import 'providers.dart';

/// Decides where a signed-out (or still loading) user may go.
String? guard(SessionStatus status, String location) {
  const signIn = '/sign-in';
  const splash = '/splash';
  return switch (status) {
    SessionStatus.loading => location == splash ? null : splash,
    SessionStatus.signedOut => location == signIn ? null : signIn,
    SessionStatus.signedIn =>
      location == signIn || location == splash ? '/' : null,
  };
}

final routerProvider = Provider<GoRouter>((ref) {
  final session = ref.watch(sessionProvider);
  final router = GoRouter(
    initialLocation: '/',
    refreshListenable: session,
    redirect: (context, state) => guard(session.status, state.matchedLocation),
    routes: [
      GoRoute(path: '/', builder: (_, _) => const HomePage()),
      GoRoute(path: '/splash', builder: (_, _) => const _Splash()),
      GoRoute(path: '/sign-in', builder: (_, _) => const SignInPage()),
      GoRoute(path: '/invite', builder: (_, _) => const InvitePage()),
      GoRoute(path: '/join', builder: (_, _) => const JoinPage()),
      GoRoute(path: '/review', builder: (_, _) => const ReviewPage()),
      GoRoute(path: '/corrections', builder: (_, _) => const CorrectionsPage()),
      GoRoute(
        path: '/pairs/:id',
        builder: (_, state) => PairPage(pairId: state.pathParameters['id']!),
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: CircularProgressIndicator()));
}
