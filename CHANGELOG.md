# Changelog

## v1.2.0 (2026-03-25)

### Features
- **Salary Analysis Engine**: 
  - Standardized salary extraction from 6+ formats (K, W/M, W/Y, Per Day, etc.) to Annualized Revenue (W/Year).
  - Skill-salary correlation calculation.
  - Automatic salary detection from job descriptions as a fallback.
- **LLM Hybrid Extraction**:
  - Added DeepSeek, Qwen (Aliyun), and Xiaomi Mimo model providers.
  - Discovery of emerging technological terms outside the fixed dictionary.
  - Cost tracking and budget monitoring for LLM usage.
- **Enhanced Excel Reports**:
  - New "🔥 High-paying Skill Analysis" sheet.
  - Integrated Average Salary column in Summary and Top50 sheets.
  - Unified multi-category sheet into a single "Category Statistics" sheet for performance.

### Optimizations
- **Performance**: 
  - Fixed Excel generation hang-up for large datasets (high category count).
  - Consolidated 1100+ fragmented skill categories into ~30 semantic categories in `skills.yaml`.
- **UX**:
  - Refined Web UI with progress tracking for both Jieba and LLM stages.

### Fixes
- Fixed regex priority conflict between monthly and annual salary formats.
- Fixed 1-indexed row insertion bug in Excel generator.
- Fixed CSV encoding detection for GB18030 formatted files.

---

## v1.1.0 (2026-03-20)
- Added Trend Analysis and Growth Rate Ranking.
- Support for time-series job data processing.

---

## v1.0.0 (2026-03-15)
- Initial release with basic skill frequency extraction and Excel export.
