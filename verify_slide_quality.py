#!/usr/bin/env python3
"""
Slide Deck Quality Verification Tool

This tool helps you verify the quality of generated slide decks by:
1. Analyzing content coherence
2. Checking provenance completeness
3. Providing detailed chunk inspection
4. Generating quality metrics
"""

import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_slide_deck(json_file: str) -> Dict[str, Any]:
    """Load slide deck from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading slide deck: {str(e)}")
        return None

def load_chunks_if_available(pdf_name: str) -> Dict[str, Any]:
    """Load chunks from vector store if available"""
    chunks_file = f"faiss_index/{pdf_name}.chunks"
    
    if not Path(chunks_file).exists():
        return {}
    
    try:
        with open(chunks_file, 'rb') as f:
            data = pickle.load(f)
        return {chunk.id: chunk for chunk in data.get('chunks', [])}
    except Exception as e:
        print(f"⚠️  Could not load chunks: {str(e)}")
        return {}

def analyze_bullet_quality(bullet: Dict[str, Any], chunks: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the quality of a single bullet point"""
    analysis = {
        'text': bullet['text'],
        'confidence': bullet['confidence'],
        'provenance_count': len(bullet['provenance']),
        'has_provenance': len(bullet['provenance']) > 0,
        'text_length': len(bullet['text']),
        'is_too_short': len(bullet['text']) < 20,
        'is_too_long': len(bullet['text']) > 200,
        'has_specific_content': any(word in bullet['text'].lower() for word in ['specific', 'example', 'data', 'result', 'finding', 'study', 'research', 'user', 'task', 'system', 'interface', 'design', 'feature', 'function', 'process', 'method', 'approach', 'implementation', 'development', 'application', 'model', 'framework', 'algorithm', 'protocol', 'standard', 'guideline', 'analysis', 'technique', 'clicking', 'checkbox', 'completed', 'focused', 'mapping', 'frictionless', 'chiming', 'accomplishment', 'pending', 'notes', 'field', 'status']),
        'source_chunks': []
    }
    
    # Analyze source chunks if available
    for chunk_id in bullet['provenance']:
        if chunk_id in chunks:
            chunk = chunks[chunk_id]
            analysis['source_chunks'].append({
                'id': chunk_id,
                'text_preview': chunk.text[:100] + '...' if len(chunk.text) > 100 else chunk.text,
                'section': chunk.metadata.get('section_title', 'Unknown'),
                'page': chunk.page_number,
                'length': len(chunk.text)
            })
        else:
            analysis['source_chunks'].append({
                'id': chunk_id,
                'text_preview': '❌ Chunk not available',
                'section': 'Unknown',
                'page': 'Unknown',
                'length': 0
            })
    
    return analysis

def calculate_quality_metrics(slide_deck: Dict[str, Any], chunks: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall quality metrics"""
    all_bullets = []
    for slide in slide_deck['slides']:
        for bullet in slide['content']:
            all_bullets.append(analyze_bullet_quality(bullet, chunks))
    
    if not all_bullets:
        return {'error': 'No bullets found'}
    
    # Calculate metrics
    total_bullets = len(all_bullets)
    bullets_with_provenance = sum(1 for b in all_bullets if b['has_provenance'])
    avg_confidence = sum(b['confidence'] for b in all_bullets) / total_bullets
    avg_length = sum(b['text_length'] for b in all_bullets) / total_bullets
    
    # Quality indicators
    too_short = sum(1 for b in all_bullets if b['is_too_short'])
    too_long = sum(1 for b in all_bullets if b['is_too_long'])
    has_specific_content = sum(1 for b in all_bullets if b['has_specific_content'])
    
    # Check for generic/placeholder content
    generic_phrases = [
        'here are the', 'key information about', 'important points',
        'this section covers', 'main topics include', 'key concepts'
    ]
    generic_bullets = sum(1 for b in all_bullets if any(phrase in b['text'].lower() for phrase in generic_phrases))
    
    return {
        'total_bullets': total_bullets,
        'bullets_with_provenance': bullets_with_provenance,
        'provenance_coverage': bullets_with_provenance / total_bullets * 100,
        'avg_confidence': avg_confidence,
        'avg_length': avg_length,
        'quality_issues': {
            'too_short_bullets': too_short,
            'too_long_bullets': too_long,
            'generic_bullets': generic_bullets,
            'bullets_without_provenance': total_bullets - bullets_with_provenance
        },
        'content_richness': {
            'specific_content_bullets': has_specific_content,
            'specific_content_ratio': has_specific_content / total_bullets * 100
        }
    }

def display_quality_report(metrics: Dict[str, Any]):
    """Display a comprehensive quality report"""
    print("\n" + "="*60)
    print("📊 SLIDE DECK QUALITY REPORT")
    print("="*60)
    
    print(f"\n📈 OVERALL METRICS:")
    print(f"   Total Bullets: {metrics['total_bullets']}")
    print(f"   Bullets with Provenance: {metrics['bullets_with_provenance']}")
    print(f"   Provenance Coverage: {metrics['provenance_coverage']:.1f}%")
    print(f"   Average Confidence: {metrics['avg_confidence']:.2f}")
    print(f"   Average Length: {metrics['avg_length']:.0f} characters")
    
    print(f"\n⚠️  QUALITY ISSUES:")
    issues = metrics['quality_issues']
    if issues['too_short_bullets'] > 0:
        print(f"   • Too Short Bullets: {issues['too_short_bullets']}")
    if issues['too_long_bullets'] > 0:
        print(f"   • Too Long Bullets: {issues['too_long_bullets']}")
    if issues['generic_bullets'] > 0:
        print(f"   • Generic/Placeholder Bullets: {issues['generic_bullets']}")
    if issues['bullets_without_provenance'] > 0:
        print(f"   • Bullets without Provenance: {issues['bullets_without_provenance']}")
    
    print(f"\n🎯 CONTENT RICHNESS:")
    richness = metrics['content_richness']
    print(f"   Specific Content Bullets: {richness['specific_content_bullets']}")
    print(f"   Specific Content Ratio: {richness['specific_content_ratio']:.1f}%")
    
    # Overall quality score
    quality_score = calculate_quality_score(metrics)
    print(f"\n🏆 OVERALL QUALITY SCORE: {quality_score}/100")
    
    if quality_score >= 80:
        print("   ✅ Excellent quality!")
    elif quality_score >= 60:
        print("   ⚠️  Good quality with room for improvement")
    else:
        print("   ❌ Poor quality - needs attention")

def calculate_quality_score(metrics: Dict[str, Any]) -> int:
    """Calculate an overall quality score out of 100"""
    score = 0
    
    # Provenance coverage (30 points)
    score += min(30, metrics['provenance_coverage'] * 0.3)
    
    # Confidence (20 points)
    score += min(20, metrics['avg_confidence'] * 20)
    
    # Content richness (25 points)
    score += min(25, metrics['content_richness']['specific_content_ratio'] * 0.25)
    
    # Length appropriateness (15 points)
    avg_length = metrics['avg_length']
    if 30 <= avg_length <= 150:
        score += 15
    elif 20 <= avg_length <= 200:
        score += 10
    else:
        score += 5
    
    # Low issue count (10 points)
    issues = metrics['quality_issues']
    total_issues = sum(issues.values())
    if total_issues == 0:
        score += 10
    elif total_issues <= 3:
        score += 7
    elif total_issues <= 6:
        score += 4
    else:
        score += 1
    
    return int(score)

def show_sample_bullets(slide_deck: Dict[str, Any], chunks: Dict[str, Any], num_samples: int = 5):
    """Show sample bullets with their provenance details"""
    print(f"\n🔍 SAMPLE BULLETS WITH PROVENANCE (showing {num_samples}):")
    print("="*60)
    
    sample_count = 0
    for slide in slide_deck['slides']:
        if sample_count >= num_samples:
            break
            
        for bullet in slide['content']:
            if sample_count >= num_samples:
                break
                
            if bullet['provenance']:  # Only show bullets with provenance
                print(f"\n📝 Bullet {sample_count + 1}:")
                print(f"   Text: {bullet['text']}")
                print(f"   Confidence: {bullet['confidence']}")
                print(f"   Source Chunks: {', '.join(bullet['provenance'])}")
                
                # Show chunk details if available
                if chunks:
                    print("   Chunk Details:")
                    for chunk_id in bullet['provenance'][:3]:  # Show first 3 chunks
                        if chunk_id in chunks:
                            chunk = chunks[chunk_id]
                            preview = chunk.text[:100] + '...' if len(chunk.text) > 100 else chunk.text
                            print(f"     • {chunk_id}: {preview}")
                        else:
                            print(f"     • {chunk_id}: ❌ Not available")
                
                sample_count += 1

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python verify_slide_quality.py <slide_deck_json_file>")
        print("Example: python verify_slide_quality.py outputs/anu_slides.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not Path(json_file).exists():
        print(f"❌ File not found: {json_file}")
        sys.exit(1)
    
    print(f"🔍 Analyzing slide deck: {json_file}")
    
    # Load slide deck
    slide_deck = load_slide_deck(json_file)
    if not slide_deck:
        sys.exit(1)
    
    # Try to load chunks
    pdf_name = Path(json_file).stem.replace('_slides', '')
    chunks = load_chunks_if_available(pdf_name)
    
    if chunks:
        print(f"✅ Loaded {len(chunks)} chunks for detailed analysis")
    else:
        print("⚠️  Chunks not available - limited analysis possible")
    
    # Calculate and display metrics
    metrics = calculate_quality_metrics(slide_deck, chunks)
    display_quality_report(metrics)
    
    # Show sample bullets
    show_sample_bullets(slide_deck, chunks)
    
    print(f"\n💡 RECOMMENDATIONS:")
    if metrics['provenance_coverage'] < 80:
        print("   • Improve provenance tracking - many bullets lack source information")
    if metrics['content_richness']['specific_content_ratio'] < 30:
        print("   • Add more specific content and examples to bullets")
    if metrics['quality_issues']['generic_bullets'] > 0:
        print("   • Replace generic placeholder text with specific content")
    if metrics['avg_confidence'] < 0.7:
        print("   • Improve confidence scores - content may be uncertain")

if __name__ == "__main__":
    main()
