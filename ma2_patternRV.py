from kivy.properties import BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior

class PatternRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    pass

class PatternLabel(RecycleDataViewBehavior, Label):
    index = None
    selected = BooleanProperty(False)
    Pattern = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super(PatternLabel, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if super(PatternLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.Pattern:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        self.selected = is_selected
        if is_selected:
            rv.selected_index = index
            rv.enableImportButton()

class PatternRecycleView(RecycleView):
    selected_index = None
    empty_text = '<nothing available>'
    empty_data = [{'text': empty_text}]

    def __init__(self, **kwargs):
        super(PatternRecycleView, self).__init__(**kwargs)
        self.data = self.empty_data

    def getSelectedData(self):
        if self.selected_index != None and self.data[self.selected_index]['text'] != self.empty_text:
            return self.data[self.selected_index] 
        else:
            return None

    def enableImportButton(self):
        self.parent.parent.importPatternButton.disabled = (self.getSelectedData() == None)