from datetime import datetime,timedelta
from pathlib import Path
import json,threading,time
from typing import List,Dict,Optional
from textual.app import App,ComposeResult
from textual.containers import Container,Horizontal
from textual.widgets import Button,Static,Input,Label,DataTable,DirectoryTree,Footer,Header,Select
from textual.screen import Screen,ModalScreen
from textual.binding import Binding
from textual import on
import pygame

class DeadlineStuff:
    def __init__(self,what:str,endtime:datetime,noise:str=None):
        self.what=what
        self.endtime=endtime
        self.noise=noise
        self.finished=False
        self.pings=self._makepings()
        self.skipped=[]
    def _makepings(self)->List[datetime]:
        right_now=datetime.now()
        diff=self.endtime-right_now
        alerts=[]
        before3h=self.endtime-timedelta(hours=3)
        if before3h>right_now:
            alerts.append(before3h)
        if diff>timedelta(days=1):
            before1d=self.endtime-timedelta(hours=24)
            if before1d>right_now:alerts.append(before1d)
        if diff>timedelta(days=3):
            before3d=self.endtime-timedelta(hours=72)
            if before3d>right_now:alerts.append(before3d)
        if diff>timedelta(weeks=1):
            before1w=self.endtime-timedelta(weeks=1)
            if before1w>right_now:alerts.append(before1w)
        return sorted(alerts)
    def serialize(self)->Dict:
        return {'what':self.what,'endtime':self.endtime.isoformat(),'noise':self.noise,'finished':self.finished,
                'pings':[p.isoformat() for p in self.pings],'skipped':[s.isoformat() for s in self.skipped]}
    @classmethod
    def deserialize(cls,stuff:Dict):
        obj=cls(stuff['what'],datetime.fromisoformat(stuff['endtime']),stuff.get('noise'))
        obj.finished=stuff.get('finished',False)
        obj.pings=[datetime.fromisoformat(p) for p in stuff.get('pings',[])]
        obj.skipped=[datetime.fromisoformat(s) for s in stuff.get('skipped',[])]
        return obj

class StartupThing(Screen):
    BINDINGS=[Binding("s","start_now","Start"),Binding("q","app.quit","Quit"),Binding("escape","app.quit","Quit")]
    def compose(self)->ComposeResult:
        with Container(id="startup-box"):
            yield Static("REMder",id="big-title")
            yield Static("Your ultimate reminder of your deadlines",id="small-text")
            with Horizontal(id="choices"):
                yield Button("Start",id="go-btn",variant="success")
                yield Button("Quit",id="exit-btn",variant="error")
        yield Footer()
    @on(Button.Pressed,"#go-btn")
    def startup(self)->None:
        self.app.push_screen(MainThing())
    @on(Button.Pressed,"#exit-btn")
    def quit(self)->None:
        self.app.exit()
    def action_start_now(self)->None:
        self.app.push_screen(MainThing())
class PopupThing(ModalScreen):
    def __init__(self):
        super().__init__()
        self.picked_day=None
        self.picked_sound=None
    def compose(self)->ComposeResult:
        years=[(str(y),y) for y in range(datetime.now().year,datetime.now().year+4)]
        months=[(f"{i:02d}",i) for i in range(1,13)]
        days=[(f"{i:02d}",i) for i in range(1,32)]
        with Container(id="popup-container"):
            yield Static("Add New Task",id="popup-header")
            yield Input(placeholder="Task name...",id="name-input")
            yield Label("Select deadline date:")
            with Horizontal(id="date-selects"):
                yield Select(years,prompt="Year",id="year-pick")
                yield Select(months,prompt="Month",id="month-pick")
                yield Select(days,prompt="Day",id="day-pick")
            yield Label("Select audio file (optional):")
            yield DirectoryTree(Path.home(),id="file-browser")
            with Horizontal():
                yield Button("Add Task",id="confirm-btn",variant="success")
                yield Button("Cancel",id="cancel-btn",variant="error")
    @on(Select.Changed,"#year-pick,#month-pick,#day-pick")
    def when_date_changed(self,event:Select.Changed)->None:
        try:
            year_sel=self.query_one("#year-pick")
            month_sel=self.query_one("#month-pick")
            day_sel=self.query_one("#day-pick")
            if year_sel.value!=Select.BLANK and month_sel.value!=Select.BLANK and day_sel.value!=Select.BLANK:
                self.picked_day=datetime(int(year_sel.value),int(month_sel.value),int(day_sel.value)).date()
        except Exception:
            pass
    @on(DirectoryTree.FileSelected)
    def when_file_picked(self,event:DirectoryTree.FileSelected)->None:
        sound_types={'.mp3','.wav','.ogg','.m4a','.flac','.aac'}
        if event.path.suffix.lower() in sound_types:
            self.picked_sound=str(event.path)
            self.query_one("#file-browser").add_class("file-selected")
    @on(Button.Pressed,"#confirm-btn")
    def confirm_task(self)->None:
        task_text=self.query_one("#name-input").value.strip()
        if not task_text or not self.picked_day:
            return
        end_of_day=datetime.combine(self.picked_day,datetime.max.time().replace(microsecond=0))
        new_task=DeadlineStuff(task_text,end_of_day,self.picked_sound)
        self.dismiss(new_task)
    @on(Button.Pressed,"#cancel-btn")
    def cancel_task(self)->None:
        self.dismiss(None)

class MainThing(Screen):
    BINDINGS=[Binding("a","add_new_task","Add Task"),Binding("d","delete_task","Delete Task"),
                Binding("ctrl q","go_back","Close whole app"),Binding("escape","go_back","Close whole app")]
    def __init__(self):
        super().__init__()
        self.stuff_list:List[DeadlineStuff]=[]
        self.save_file=Path.home()/".remder_stuff.json"
        self.load_from_disk()
    def compose(self)->ComposeResult:
        yield Header()
        with Container(id="main-box"):
            yield Static("Your Tasks & Deadlines",id="main-header")
            yield DataTable(id="stuff-table")
            with Horizontal():
                yield Button("Add Task",id="new-task-btn",variant="success")
                yield Button("Delete Selected",id="remove-btn",variant="error")
        yield Footer()
    def on_mount(self)->None:
        table=self.query_one("#stuff-table")
        table.add_columns("Task","Deadline","Status","Next Alarm")
        self.update_display()
        monitor_thread=threading.Thread(target=self.watch_alarms,daemon=True)
        monitor_thread.start()
    def update_display(self)->None:
        table=self.query_one("#stuff-table")
        table.clear()
        for item in self.stuff_list:
            status_text="✓ Completed" if item.finished else "⏰ Pending"
            next_ping="None"
            if not item.finished and item.pings:
                current_time=datetime.now()
                upcoming=[p for p in item.pings if p>current_time]
                if upcoming:
                    next_ping=upcoming[0].strftime("%Y-%m-%d %H:%M")
            table.add_row(item.what,item.endtime.strftime("%Y-%m-%d %H:%M"),status_text,next_ping)
    @on(Button.Pressed,"#new-task-btn")
    def create_task(self)->None:
        self.app.push_screen(PopupThing(),self.handle_new_task)
    def handle_new_task(self,task:Optional[DeadlineStuff])->None:
        if task:
            self.stuff_list.append(task)
            self.save_to_disk()
            self.update_display()
    @on(Button.Pressed,"#remove-btn")
    def remove_task(self)->None:
        table=self.query_one("#stuff-table")
        if table.cursor_row<len(self.stuff_list):
            del self.stuff_list[table.cursor_row]
            self.save_to_disk()
            self.update_display()
    def go_back(self)->None:
        self.app.pop_screen()
    def action_add_new_task(self)->None:
        self.app.push_screen(PopupThing(),self.handle_new_task)

    def action_delete_task(self)->None:
        table=self.query_one("#stuff-table")
        if table.cursor_row<len(self.stuff_list):
            del self.stuff_list[table.cursor_row]
            self.save_to_disk()
            self.update_display()
    def save_to_disk(self)->None:
        try:
            data=[item.serialize() for item in self.stuff_list]
            with open(self.save_file,'w') as f:
                json.dump(data,f,indent=2)
        except Exception:
            pass
    def load_from_disk(self)->None:
        try:
            if self.save_file.exists():
                with open(self.save_file,'r') as f:
                    data=json.load(f)
                self.stuff_list=[DeadlineStuff.deserialize(item_data) for item_data in data]
        except Exception:
            self.stuff_list=[]
    def watch_alarms(self)->None:
        pygame.mixer.init()
        while True:
            current_time=datetime.now()
            for item in self.stuff_list:
                if item.finished:
                    continue
                for ping_time in item.pings[:]:
                    if ping_time<=current_time and ping_time not in item.skipped:
                        self.make_noise(item,ping_time)
                        item.pings.remove(ping_time)
                if item.endtime<=current_time:
                    self.deadline_reached(item)
                    item.finished=True
            self.save_to_disk()
            time.sleep(60)
    def make_noise(self,item:DeadlineStuff,ping_time:datetime)->None:
        if item.noise and Path(item.noise).exists():
            try:
                pygame.mixer.music.load(item.noise)
                pygame.mixer.music.play()
            except Exception:
                pass
        self.call_from_thread(self.update_display)
    def deadline_reached(self,item:DeadlineStuff)->None:
        pass

class RemderThingy(App):
    TITLE="REMder - Your Ultimate Deadline Reminder"
    CSS_PATH="main.css"
    def on_mount(self)->None:
        self.push_screen(StartupThing())

if __name__=="__main__":
    app=RemderThingy()
    app.run()
