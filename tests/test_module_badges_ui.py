import os
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout
from qt_app import marquer_module

def test_module_badges_rights_expiration_and_render():
    app = QApplication.instance() or QApplication([])
    class Preferences:
        def __init__(self, theme): self.theme = theme
        def preferences(self): return {'theme': self.theme}
    for theme in ('Clair', 'Sombre'):
        window = QWidget();window.gestion_comptes = Preferences(theme)
        layout = QVBoxLayout(window)
        label = QLabel();layout.addWidget(label)
        for state, wanted in [({'active':False,'modules':['finance_tva']},False),
                              ({'active':True,'modules':['administratif']},False),
                              ({'active':True,'modules':['finance_tva']},True),
                              ({'active':False,'modules':[]},False)]:
            assert marquer_module(label, 'Finances et TVA', 'finance_tva', state) is wanted
            assert ('Activé' if wanted else 'À débloquer') in label.text()
            assert label.property('module_active') is wanted
            assert label.accessibleName().endswith('Activé' if wanted else 'À débloquer')
        for title,module,state in [('Finances et TVA','finance_tva',{'active':False,'modules':[]}),
                                  ('Préparation administrative','administratif',{'active':False,'modules':[]}),
                                  ('Finances et TVA','finance_tva',{'active':True,'modules':['finance_tva']}),
                                  ('Dépenses détaillées HT / TVA / TTC','finance_tva',{'active':False,'modules':[]})]:
            button=QPushButton();layout.addWidget(button);marquer_module(button,title,module,state)
        window.setStyleSheet('QWidget {background:'+('#171d28' if theme=='Sombre' else '#f4f6f9')+';}')
        window.resize(440,380);window.show();app.processEvents()
        if os.environ.get('GITHUB_ACTIONS'):
            output=Path('distribution')/('module-ui-'+theme.lower()+'.png')
            assert window.grab().save(str(output))
        window.close();window.deleteLater();app.processEvents()
