"""Qt stylesheets for Feed Converter Desktop."""

APP_STYLESHEET = """
QWidget#Root { background: #F5F7FB; color: #172033; }
QFrame#Sidebar { background: #FFFFFF; border-right: 1px solid #E6EAF2; }
QFrame#Content { background: #F5F7FB; }
QLabel#AppTitle { font-size: 24px; font-weight: 800; color: #111827; }
QLabel#VersionText { font-size: 12px; color: #8390A3; }
QLabel#SectionLabel { font-size: 12px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-top: 10px; }
QLabel#PageTitle { font-size: 28px; font-weight: 800; color: #111827; }
QLabel#CardTitle { font-size: 30px; font-weight: 800; color: #111827; }
QLabel#MutedText { font-size: 13px; color: #6B7280; }
QLabel#InfoText { font-size: 14px; color: #374151; line-height: 1.4; }
QFrame#ProjectCard { background: #FFFFFF; border: 1px solid #E6EAF2; border-radius: 22px; }
QFrame#MetricsBox { background: #F8FAFD; border: 1px solid #E8EDF5; border-radius: 18px; }
QFrame#MetricCard { background: #FFFFFF; border: 1px solid #E9EEF6; border-radius: 14px; }
QLabel#MetricValue { font-size: 22px; font-weight: 800; color: #0F172A; }
QLabel#MetricLabel { font-size: 12px; color: #6B7280; }
QPushButton { border: none; border-radius: 12px; padding: 11px 16px; font-weight: 700; }
QPushButton#PrimaryButton { background: #2563EB; color: white; }
QPushButton#PrimaryButton:hover { background: #1D4ED8; }
QPushButton#SecondaryButton { background: #EEF2FF; color: #1E3A8A; }
QPushButton#SecondaryButton:hover { background: #E0E7FF; }
QListWidget#ProjectList { background: #F8FAFD; border: 1px solid #E6EAF2; border-radius: 16px; padding: 8px; outline: none; }
QListWidget#ProjectList::item { padding: 10px; border-radius: 12px; color: #1F2937; }
QListWidget#ProjectList::item:selected { background: #E0ECFF; color: #0F172A; }
QMenuBar { background: #FFFFFF; border-bottom: 1px solid #E6EAF2; }
QMenuBar::item { padding: 6px 10px; }
QMenu { background: #FFFFFF; border: 1px solid #E6EAF2; }
QMenu::item { padding: 8px 22px; }
"""
