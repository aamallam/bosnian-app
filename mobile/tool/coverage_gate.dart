// Fails when line coverage of hand-written code (generated localisations
// excluded) drops below the minimum.
//
//   flutter test --coverage && dart run tool/coverage_gate.dart 85
// ignore_for_file: avoid_print
import 'dart:io';

void main(List<String> args) {
  final minimum = double.parse(args.isEmpty ? '85' : args.first);
  var total = 0;
  var hit = 0;
  var skip = false;
  for (final line in File('coverage/lcov.info').readAsLinesSync()) {
    if (line.startsWith('SF:')) {
      skip = line.contains('l10n');
    } else if (!skip && line.startsWith('DA:')) {
      total++;
      if (int.parse(line.split(',')[1]) > 0) hit++;
    }
  }
  final percent = total == 0 ? 0 : 100 * hit / total;
  print('Line coverage: ${percent.toStringAsFixed(1)}% ($hit/$total)');
  if (percent < minimum) {
    print('Below the minimum of $minimum%.');
    exit(1);
  }
}
