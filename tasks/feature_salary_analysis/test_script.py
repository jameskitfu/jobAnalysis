import sys
sys.path.append('.')
from services.salary_analyzer import SalaryAnalyzer

analyzer = SalaryAnalyzer()
tests = [
    "15-25K·14薪",
    "20-35k*15",
    "300-400元/天",
    "2.5万-3.5万/月",
    "8k",
    "面议",
    "40-60k·16薪",
    "150-200元/天",
    "18-25K",
    "5k",
    "30k-40k*14"
]

for t in tests:
    print(f"{t} -> {analyzer.parse_annual_salary(t)}")
