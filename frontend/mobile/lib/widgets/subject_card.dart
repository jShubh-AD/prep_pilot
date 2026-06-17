import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SubjectCard extends StatefulWidget {
  final Subject subject;
  final VoidCallback onTap;
  final int index;

  const SubjectCard({
    super.key,
    required this.subject,
    required this.onTap,
    required this.index,
  });

  @override
  State<SubjectCard> createState() => _SubjectCardState();
}

class _SubjectCardState extends State<SubjectCard> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  bool _isHovered = false;

  final List<List<Color>> _gradients = [
    [const Color(0xFF6366F1), const Color(0xFF4F46E5)], // Indigo
    [const Color(0xFFEC4899), const Color(0xFFD946EF)], // Pink-Purple
    [const Color(0xFF14B8A6), const Color(0xFF0D9488)], // Teal
    [const Color(0xFFF59E0B), const Color(0xFFD97706)], // Amber
    [const Color(0xFF3B82F6), const Color(0xFF2563EB)], // Blue
    [const Color(0xFF8B5CF6), const Color(0xFF7C3AED)], // Purple
  ];

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 150),
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.96).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  List<Color> _getGradient() {
    return _gradients[widget.index % _gradients.length];
  }

  IconData _getIcon() {
    final name = widget.subject.subjectName.toLowerCase();
    if (name.contains('java') || name.contains('oop')) {
      return Icons.code;
    } else if (name.contains('attention') || name.contains('ai') || name.contains('model')) {
      return Icons.psychology;
    } else if (name.contains('os') || name.contains('system')) {
      return Icons.settings_applications;
    } else if (name.contains('db') || name.contains('sql')) {
      return Icons.storage;
    } else if (name.contains('math') || name.contains('alg')) {
      return Icons.functions;
    }
    return Icons.menu_book;
  }

  @override
  Widget build(BuildContext context) {
    final colors = _getGradient();
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTapDown: (_) => _controller.forward(),
        onTapUp: (_) {
          _controller.reverse();
          widget.onTap();
        },
        onTapCancel: () => _controller.reverse(),
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: colors,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(24.0),
              boxShadow: [
                BoxShadow(
                  color: colors[1].withOpacity(_isHovered ? 0.5 : 0.3),
                  blurRadius: _isHovered ? 20.0 : 12.0,
                  offset: Offset(0, _isHovered ? 8.0 : 4.0),
                )
              ],
            ),
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(16.0),
                      ),
                      padding: const EdgeInsets.all(12.0),
                      child: Icon(
                        _getIcon(),
                        color: Colors.white,
                        size: 28.0,
                      ),
                    ),
                    if (widget.subject.subjectCode != null && widget.subject.subjectCode!.isNotEmpty)
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12.0),
                        ),
                        padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 4.0),
                        child: Text(
                          widget.subject.subjectCode!,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 12.0,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 12.0),
                Text(
                  widget.subject.subjectName,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20.0,
                    fontWeight: FontWeight.bold,
                    height: 1.2,
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      'Start Now',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.9),
                        fontWeight: FontWeight.w600,
                        fontSize: 14.0,
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Icon(
                      Icons.arrow_forward,
                      color: Colors.white,
                      size: 12.0,
                    ),
                  ],
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}
