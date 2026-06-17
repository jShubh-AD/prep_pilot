import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('Dashboard basic smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());

    // Verify that the title "PrepPilot" is present.
    expect(find.text('PrepPilot'), findsOneWidget);
    
    // Verify that the subtitle is present.
    expect(find.text('Your AI Exam Prep Companion'), findsOneWidget);
  });
}
