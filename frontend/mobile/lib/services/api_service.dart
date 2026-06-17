import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class Subject {
  final String subjectId;
  final String subjectName;
  final String? university;
  final String? subjectCode;

  Subject({
    required this.subjectId,
    required this.subjectName,
    this.university,
    this.subjectCode,
  });

  factory Subject.fromJson(Map<String, dynamic> json) {
    return Subject(
      subjectId: json['subject_id'] ?? '',
      subjectName: json['subject_name'] ?? '',
      university: json['university'],
      subjectCode: json['subject_code'],
    );
  }
}

class QueryResponse {
  final String answer;
  final List<String> llmContext;
  final List<Map<String, dynamic>> dbFound;

  QueryResponse({
    required this.answer,
    required this.llmContext,
    required this.dbFound,
  });

  factory QueryResponse.fromJson(Map<String, dynamic> json) {
    final data = json['data'] as Map<String, dynamic>? ?? {};
    
    final contextList = data['llm_context'] as List<dynamic>? ?? [];
    final dbFoundList = data['db_found'] as List<dynamic>? ?? [];

    return QueryResponse(
      answer: data['answer'] ?? 'No answer provided.',
      llmContext: contextList.map((e) => e.toString()).toList(),
      dbFound: dbFoundList.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
    );
  }
}

class ApiService {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://192.168.1.7:8000';
    } else {
      try {
        if (Platform.isAndroid) {
          return 'http://192.168.1.7:8000';
        }
      } catch (e) {
        // Fallback for non-android systems or platforms where Platform.isAndroid throws
      }
      return 'http://192.168.1.7:8000';
    }
  }

  // Fetch all subjects from Backend
  static Future<List<Subject>> fetchSubjects() async {
    final url = Uri.parse('$baseUrl/subjects');
    try {
      final response = await http.get(url).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => Subject.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load subjects. Status code: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to connect to backend: $e');
    }
  }

  // Send query to LLM RAG endpoint
  static Future<QueryResponse> querySubject(String query, String subjectId, {int topK = 5}) async {
    final url = Uri.parse('$baseUrl/query');
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'query': query,
          'subject': subjectId,
          'top_k': topK,
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);
        if (data['success'] == true) {
          return QueryResponse.fromJson(data);
        } else {
          throw Exception('Backend reported failure in query');
        }
      } else {
        final errorMsg = jsonDecode(response.body)['detail'] ?? 'Unknown error';
        throw Exception(errorMsg);
      }
    } catch (e) {
      throw Exception('Failed to get answer: $e');
    }
  }
}
