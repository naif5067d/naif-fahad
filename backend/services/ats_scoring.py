"""
ATS Smart Scoring Engine
C-A Style: Strict on fluff, fair to young talent with evidence
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


# ==================== CONFIGURATION ====================

DEFAULT_WEIGHTS = {
    "skill_match": 25,
    "experience": 20,
    "education": 15,
    "language": 10,
    "stability": 15,
    "evidence": 10,
    # Penalties (subtracted)
    "fluff_penalty_max": 15,
    "ego_penalty_max": 10,
    "stuffing_penalty_max": 10,
}

CLASSIFICATION_THRESHOLDS = {
    "excellent": 85,
    "strong": 70,
    "acceptable": 55,
    # Below 55 = Weak
}

# Fluff phrases - generic claims without evidence
FLUFF_PHRASES_EN = [
    "work under pressure", "team player", "fast learner", "self-motivated",
    "highly skilled", "hard worker", "detail oriented", "results driven",
    "excellent communication", "problem solver", "quick learner", "passionate",
    "dynamic", "proactive", "dedicated", "motivated", "enthusiastic",
    "strong work ethic", "multitasking", "time management", "leadership skills",
    "interpersonal skills", "organizational skills", "analytical skills",
]

FLUFF_PHRASES_AR = [
    "تحمل ضغط العمل", "العمل الجماعي", "سريع التعلم", "الالتزام",
    "طموح", "مهارات عالية", "روح الفريق", "التفاني في العمل",
    "مهارات التواصل", "حل المشكلات", "الدقة في العمل", "الشغف",
    "ديناميكي", "استباقي", "ملتزم", "متحمس", "نشيط",
    "أخلاقيات عمل قوية", "تعدد المهام", "إدارة الوقت", "مهارات قيادية",
    "مهارات التعامل", "مهارات تنظيمية", "مهارات تحليلية", "العمل تحت الضغط",
]

# Evidence indicators
EVIDENCE_PATTERNS = [
    r'\d+%',  # Percentages
    r'\$[\d,]+', r'[\d,]+\s*(ريال|SAR|USD|دولار)',  # Money
    r'\d+\s*(project|مشروع|client|عميل)',  # Project counts
    r'(increased|decreased|improved|reduced|saved|achieved)\s+\d+',
    r'(زيادة|تقليل|تحسين|توفير|إنجاز)\s+\d+',
    r'\d+\s*(year|سنة|month|شهر|week|أسبوع)',  # Time periods
    r'(led|managed|supervised)\s+\d+',  # Team size
    r'(قاد|أدار|أشرف على)\s+\d+',
]

# Ego pronouns
EGO_PRONOUNS_EN = ['i ', 'i\'m', 'my ', 'me ', 'myself']
EGO_PRONOUNS_AR = ['أنا', 'لي', 'لدي', 'بنفسي']
TEAM_WORDS_EN = ['we ', 'our ', 'team', 'collaborated', 'together']
TEAM_WORDS_AR = ['نحن', 'فريق', 'تعاون', 'معاً', 'بالتعاون']

# Common skills synonyms
SKILL_SYNONYMS = {
    # English
    "excel": ["excel", "spreadsheet", "spreadsheets", "microsoft excel"],
    "word": ["word", "microsoft word", "ms word"],
    "accounting": ["accounting", "bookkeeping", "financial reporting", "ledger"],
    "management": ["management", "managing", "manager", "leadership", "lead"],
    "programming": ["programming", "coding", "developer", "software", "python", "java"],
    "design": ["design", "designer", "graphic", "photoshop", "illustrator", "ui", "ux"],
    "sales": ["sales", "selling", "revenue", "business development"],
    "marketing": ["marketing", "digital marketing", "seo", "social media"],
    # Arabic
    "محاسبة": ["محاسبة", "محاسب", "القيود", "الدفاتر", "المالية"],
    "إدارة": ["إدارة", "مدير", "قيادة", "إشراف"],
    "تصميم": ["تصميم", "مصمم", "جرافيك", "فوتوشوب"],
    "مبيعات": ["مبيعات", "بيع", "تسويق", "عملاء"],
    "برمجة": ["برمجة", "مطور", "تطوير", "بايثون", "جافا"],
}


@dataclass
class ScoringResult:
    score: int = 0
    auto_class: str = "Weak"
    tier: str = "C"
    ats_readable: bool = True
    
    # Detailed scores (0-100)
    skill_match_score: int = 0
    experience_score: int = 0
    education_score: int = 0
    language_score: int = 0
    stability_score: int = 0
    evidence_score: int = 0
    
    # Risk indicators
    fluff_ratio: float = 0.0
    ego_index: float = 0.0
    stuffing_risk: float = 0.0
    stability_risk: float = 0.0
    
    # Penalties applied
    fluff_penalty: int = 0
    ego_penalty: int = 0
    stuffing_penalty: int = 0
    
    # Analysis
    top_reasons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    
    # Flags
    high_potential: bool = False
    high_potential_reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "auto_class": self.auto_class,
            "tier": self.tier,
            "ats_readable": self.ats_readable,
            "skill_match_score": self.skill_match_score,
            "experience_score": self.experience_score,
            "education_score": self.education_score,
            "language_score": self.language_score,
            "stability_score": self.stability_score,
            "evidence_score": self.evidence_score,
            "fluff_ratio": round(self.fluff_ratio, 2),
            "ego_index": round(self.ego_index, 2),
            "stuffing_risk": round(self.stuffing_risk, 2),
            "stability_risk": round(self.stability_risk, 2),
            "fluff_penalty": self.fluff_penalty,
            "ego_penalty": self.ego_penalty,
            "stuffing_penalty": self.stuffing_penalty,
            "top_reasons": self.top_reasons[:3],
            "risks": self.risks[:3],
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "high_potential": self.high_potential,
            "high_potential_reason": self.high_potential_reason,
        }


class ATSScoringEngine:
    """Smart ATS Scoring Engine with C-A style evaluation"""
    
    def __init__(self, job_requirements: Dict = None, weights: Dict = None):
        self.job = job_requirements or {}
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.result = ScoringResult()
    
    def score(self, cv_text: str, is_readable: bool = True) -> ScoringResult:
        """
        Main scoring function
        """
        self.result = ScoringResult()
        self.result.ats_readable = is_readable
        
        # For unreadable CVs, mark for manual review instead of rejecting
        if not is_readable or not cv_text or len(cv_text.strip()) < 100:
            self.result.score = 0
            self.result.auto_class = "Manual Review"
            self.result.tier = "C"  # Put in Tier C for manual review
            self.result.risks.append("CV requires manual review - not machine-readable")
            self.result.top_reasons.append("File uploaded but needs HR review")
            return self.result
        
        cv_lower = cv_text.lower()
        
        # Calculate individual scores
        self._calc_skill_match(cv_lower)
        self._calc_experience(cv_text)
        self._calc_education(cv_lower)
        self._calc_language(cv_text)
        self._calc_stability(cv_text)
        self._calc_evidence(cv_text)
        
        # Calculate risk indicators
        self._calc_fluff_ratio(cv_lower)
        self._calc_ego_index(cv_lower)
        self._calc_stuffing_risk(cv_lower)
        
        # Calculate final score
        self._calc_final_score()
        
        # Check high potential flag
        self._check_high_potential()
        
        # Classify
        self._classify()
        
        # Generate reasons
        self._generate_analysis()
        
        return self.result
    
    def _calc_skill_match(self, cv_lower: str):
        """Calculate skill match percentage"""
        required_skills = self.job.get('required_skills', '')
        if not required_skills:
            self.result.skill_match_score = 70  # Neutral if no requirements
            return
        
        skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        if not skills_list:
            self.result.skill_match_score = 70
            return
        
        matched = []
        missing = []
        
        for skill in skills_list:
            # Check direct match
            if skill in cv_lower:
                matched.append(skill)
                continue
            
            # Check synonyms
            found = False
            for key, synonyms in SKILL_SYNONYMS.items():
                if skill in key.lower() or skill in [s.lower() for s in synonyms]:
                    for syn in synonyms:
                        if syn.lower() in cv_lower:
                            matched.append(skill)
                            found = True
                            break
                if found:
                    break
            
            if not found:
                missing.append(skill)
        
        self.result.matched_skills = matched
        self.result.missing_skills = missing
        
        if skills_list:
            self.result.skill_match_score = int((len(matched) / len(skills_list)) * 100)
    
    def _calc_experience(self, cv_text: str):
        """Estimate years of experience"""
        required_years = self.job.get('experience_years', 0)
        
        # Look for experience patterns
        patterns = [
            r'(\d+)\+?\s*(?:years?|سنة|سنوات)\s*(?:of\s*)?(?:experience|خبرة)',
            r'(?:experience|خبرة)[:\s]*(\d+)\+?\s*(?:years?|سنة|سنوات)',
            r'(\d{4})\s*[-–]\s*(?:present|current|حالي|الآن)',
        ]
        
        max_years = 0
        for pattern in patterns:
            matches = re.findall(pattern, cv_text.lower(), re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 4:  # Year like 2020
                        years = datetime.now().year - int(match)
                    else:
                        years = int(match)
                    max_years = max(max_years, years)
                except:
                    pass
        
        if required_years > 0:
            ratio = min(max_years / required_years, 1.5)  # Cap at 150%
            self.result.experience_score = int(min(ratio * 70 + 30, 100))
        else:
            self.result.experience_score = 70 if max_years > 0 else 50
    
    def _calc_education(self, cv_lower: str):
        """Score education level"""
        education_keywords = {
            'phd': 100, 'doctorate': 100, 'دكتوراه': 100,
            'master': 90, 'mba': 90, 'ماجستير': 90,
            'bachelor': 80, 'bsc': 80, 'ba': 80, 'بكالوريوس': 80,
            'diploma': 60, 'دبلوم': 60,
            'certificate': 50, 'شهادة': 50,
            'high school': 40, 'ثانوي': 40,
        }
        
        max_score = 0
        for keyword, score in education_keywords.items():
            if keyword in cv_lower:
                max_score = max(max_score, score)
        
        self.result.education_score = max_score if max_score > 0 else 50
    
    def _calc_language(self, cv_text: str):
        """Score language proficiency"""
        required_langs = self.job.get('required_languages', ['ar'])
        if isinstance(required_langs, str):
            required_langs = [required_langs]
        
        score = 0
        
        # Check Arabic content (at least 50 characters)
        has_arabic = len(re.findall(r'[\u0600-\u06FF]', cv_text)) >= 50
        has_english = len(re.findall(r'[a-zA-Z]', cv_text)) >= 50
        
        # Score based on required languages
        if 'ar' in required_langs and has_arabic:
            score += 50
        if 'en' in required_langs and has_english:
            score += 50
        
        # Bonus for both languages if both required
        if len(required_langs) >= 2 and has_arabic and has_english:
            score = min(score + 20, 100)
        
        # Check for language proficiency mentions
        lang_keywords = ['fluent', 'native', 'proficient', 'bilingual', 'طلاقة', 'إجادة', 'ثنائي اللغة', 'جيد جداً', 'ممتاز']
        for kw in lang_keywords:
            if kw in cv_text.lower():
                score = min(score + 10, 100)
                break
        
        # If no required languages specified, give neutral score if any language found
        if not required_langs and (has_arabic or has_english):
            score = 70
        
        self.result.language_score = score
    
    def _calc_stability(self, cv_text: str):
        """Calculate job stability (penalize frequent changes)"""
        # Find year patterns
        years = re.findall(r'20\d{2}', cv_text)
        years = sorted(set([int(y) for y in years if 2000 <= int(y) <= datetime.now().year]))
        
        if len(years) < 2:
            self.result.stability_score = 70
            self.result.stability_risk = 0.3
            return
        
        # Calculate average tenure
        job_count = len(years)
        span = years[-1] - years[0]
        
        if span > 0 and job_count > 1:
            avg_tenure = span / (job_count - 1)
            
            if avg_tenure >= 3:
                self.result.stability_score = 100
                self.result.stability_risk = 0.0
            elif avg_tenure >= 2:
                self.result.stability_score = 85
                self.result.stability_risk = 0.2
            elif avg_tenure >= 1:
                self.result.stability_score = 65
                self.result.stability_risk = 0.4
            else:
                self.result.stability_score = 40
                self.result.stability_risk = 0.7
        else:
            self.result.stability_score = 70
            self.result.stability_risk = 0.3
    
    def _calc_evidence(self, cv_text: str):
        """Score evidence of achievements"""
        evidence_count = 0
        
        for pattern in EVIDENCE_PATTERNS:
            matches = re.findall(pattern, cv_text, re.IGNORECASE)
            evidence_count += len(matches)
        
        # Score based on evidence count
        if evidence_count >= 10:
            self.result.evidence_score = 100
        elif evidence_count >= 7:
            self.result.evidence_score = 85
        elif evidence_count >= 4:
            self.result.evidence_score = 70
        elif evidence_count >= 2:
            self.result.evidence_score = 55
        else:
            self.result.evidence_score = 30
    
    def _calc_fluff_ratio(self, cv_lower: str):
        """Calculate fluff phrase ratio"""
        fluff_count = 0
        total_words = len(cv_lower.split())
        
        for phrase in FLUFF_PHRASES_EN + FLUFF_PHRASES_AR:
            count = cv_lower.count(phrase.lower())
            fluff_count += count
        
        if total_words > 0:
            self.result.fluff_ratio = min((fluff_count * 10) / total_words, 1.0)
        
        # Calculate penalty
        self.result.fluff_penalty = int(self.result.fluff_ratio * self.weights['fluff_penalty_max'])
    
    def _calc_ego_index(self, cv_lower: str):
        """Calculate ego vs team language ratio"""
        ego_count = sum(cv_lower.count(p) for p in EGO_PRONOUNS_EN + EGO_PRONOUNS_AR)
        team_count = sum(cv_lower.count(p) for p in TEAM_WORDS_EN + TEAM_WORDS_AR)
        
        # Add 1 to avoid division by zero and reduce sensitivity
        total = ego_count + team_count + 1
        self.result.ego_index = ego_count / total
        
        # Penalty only if very high ego without evidence
        # Note: CVs naturally use "I" - only penalize extreme cases with no team words
        if self.result.ego_index > 0.9 and team_count == 0 and self.result.evidence_score < 50:
            self.result.ego_penalty = int((self.result.ego_index - 0.7) * self.weights['ego_penalty_max'])
        else:
            self.result.ego_penalty = 0
    
    def _calc_stuffing_risk(self, cv_lower: str):
        """Detect keyword stuffing"""
        required_skills = self.job.get('required_skills', '')
        if not required_skills:
            self.result.stuffing_risk = 0.0
            return
        
        skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        
        stuffing_score = 0
        for skill in skills_list:
            count = cv_lower.count(skill)
            if count > 5:  # Suspicious repetition
                stuffing_score += (count - 5) * 0.1
        
        self.result.stuffing_risk = min(stuffing_score, 1.0)
        self.result.stuffing_penalty = int(self.result.stuffing_risk * self.weights['stuffing_penalty_max'])
    
    def _calc_final_score(self):
        """Calculate weighted final score"""
        weighted_score = (
            self.result.skill_match_score * (self.weights['skill_match'] / 100) +
            self.result.experience_score * (self.weights['experience'] / 100) +
            self.result.education_score * (self.weights['education'] / 100) +
            self.result.language_score * (self.weights['language'] / 100) +
            self.result.stability_score * (self.weights['stability'] / 100) +
            self.result.evidence_score * (self.weights['evidence'] / 100)
        )
        
        # Apply penalties
        total_penalty = (
            self.result.fluff_penalty +
            self.result.ego_penalty +
            self.result.stuffing_penalty
        )
        
        self.result.score = max(0, int(weighted_score - total_penalty))
    
    def _check_high_potential(self):
        """Check for high potential flag (C-A fairness for young talent)"""
        required_years = self.job.get('experience_years', 0)
        
        if (self.result.skill_match_score >= 75 and 
            self.result.evidence_score >= 70 and
            self.result.experience_score < 70 and
            required_years > 0):
            
            self.result.high_potential = True
            self.result.high_potential_reason = "Strong skills and evidence despite limited experience"
    
    def _classify(self):
        """Classify application into tier and class"""
        score = self.result.score
        
        # Classification
        if score >= CLASSIFICATION_THRESHOLDS['excellent']:
            self.result.auto_class = "Excellent"
        elif score >= CLASSIFICATION_THRESHOLDS['strong']:
            self.result.auto_class = "Strong"
        elif score >= CLASSIFICATION_THRESHOLDS['acceptable']:
            self.result.auto_class = "Acceptable"
        else:
            self.result.auto_class = "Weak"
        
        # Tier assignment
        if score >= 85 and self.result.stability_risk < 0.5:
            self.result.tier = "A"
        elif score >= 55:
            self.result.tier = "B"
        else:
            self.result.tier = "C"
        
        # High potential can bump to B
        if self.result.high_potential and self.result.tier == "C":
            self.result.tier = "B"
    
    def _generate_analysis(self):
        """Generate top reasons and risks"""
        # Top reasons (strengths)
        reasons = []
        
        if self.result.skill_match_score >= 80:
            reasons.append(f"Strong skill match ({self.result.skill_match_score}%)")
        if self.result.evidence_score >= 70:
            reasons.append("Good evidence of achievements")
        if self.result.experience_score >= 80:
            reasons.append("Solid experience level")
        if self.result.education_score >= 80:
            reasons.append("Strong educational background")
        if self.result.stability_score >= 85:
            reasons.append("Stable career history")
        if self.result.high_potential:
            reasons.append("High potential candidate")
        
        # Default reasons
        if not reasons:
            if self.result.skill_match_score >= 50:
                reasons.append(f"Partial skill match ({self.result.skill_match_score}%)")
            if self.result.language_score >= 70:
                reasons.append("Good language proficiency")
        
        self.result.top_reasons = reasons[:3]
        
        # Risks
        risks = []
        
        if self.result.fluff_ratio > 0.3:
            risks.append(f"High fluff ratio ({int(self.result.fluff_ratio * 100)}%)")
        if self.result.ego_index > 0.7:
            risks.append("Excessive self-focus without team context")
        if self.result.stuffing_risk > 0.3:
            risks.append("Possible keyword stuffing detected")
        if self.result.stability_risk > 0.5:
            risks.append("Frequent job changes detected")
        if self.result.evidence_score < 40:
            risks.append("Lacks measurable achievements")
        if self.result.missing_skills:
            risks.append(f"Missing skills: {', '.join(self.result.missing_skills[:3])}")
        
        self.result.risks = risks[:3]


# Convenience function
async def score_application(cv_text: str, job_requirements: Dict, is_readable: bool = True) -> Dict:
    """Score a CV against job requirements"""
    engine = ATSScoringEngine(job_requirements)
    result = engine.score(cv_text, is_readable)
    return result.to_dict()
