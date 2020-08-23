from brain_brew.representation.yaml.my_yaml import YamlRepr
from dataclasses import dataclass
from typing import List, Optional, Dict, Set

from brain_brew.utils import find_media_in_field

FIELDS = 'fields'
GUID = 'guid'
TAGS = 'tags'
NOTE_MODEL = 'note_model'
FLAGS = "flags"
NOTES = "notes"
NOTE_GROUPINGS = "note_groupings"
MEDIA_REFERENCES = "media_references"


@dataclass
class GroupableNoteData(YamlRepr):
    note_model: Optional[str]
    tags: Optional[List[str]]

    def encode_groupable(self, data_dict):
        if self.note_model is not None:
            data_dict.setdefault(NOTE_MODEL, self.note_model)
        if self.tags is not None and self.tags != []:
            data_dict.setdefault(TAGS, self.tags)
        return data_dict


@dataclass
class Note(GroupableNoteData):
    fields: List[str]
    guid: str
    flags: int
    # media_references: Optional[Set[str]]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            fields=data.get(FIELDS),
            guid=data.get(GUID),
            note_model=data.get(NOTE_MODEL, None),
            tags=data.get(TAGS, None),
            flags=data.get(FLAGS, 0)
        )

    def encode(self) -> dict:
        data_dict: Dict[str, any] = {FIELDS: self.fields, GUID: self.guid}
        if self.flags is not None and self.flags != 0:
            data_dict.setdefault(FLAGS, self.flags)
        super().encode_groupable(data_dict)
        return data_dict

    def get_media_references(self) -> Set[str]:
        return {entry for field in self.fields for entry in find_media_in_field(field)}


@dataclass
class NoteGrouping(GroupableNoteData):
    notes: List[Note]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            notes=list(map(Note.from_dict, data.get(NOTES))),
            note_model=data.get(NOTE_MODEL, None),
            tags=data.get(TAGS, None)
        )

    def encode(self) -> dict:
        data_dict = {}
        super().encode_groupable(data_dict)
        data_dict.setdefault(NOTES, [note.encode() for note in self.notes])
        return data_dict

    # TODO: Extract Shared Tags and Note Models
    # TODO: Sort notes
    # TODO: Set data

    def verify_groupings(self):
        errors = []
        if self.note_model is not None:
            if any([note.note_model for note in self.notes]):
                errors.append(ValueError(f"NoteGrouping for 'note_model' {self.note_model} has notes with 'note_model'."
                                         f" Please remove one of these."))
        return errors

    def get_all_known_note_model_names(self) -> set:
        return {self.note_model} if self.note_model else {note.note_model for note in self.notes}

    def get_all_media_references(self) -> set:
        all_media = set()
        for note in self.notes:
            for media in note.get_media_references():
                all_media = all_media.union(media)
        return all_media

    def get_all_notes_copy(self) -> List[Note]:
        def join_tags(n_tags):
            if self.tags is None and n_tags is None:
                return []
            elif self.tags is None:
                return n_tags
            elif n_tags is None:
                return self.tags
            else:
                return [*n_tags, *self.tags]

        return [Note(
                    note_model=self.note_model if self.note_model is not None else n.note_model,
                    tags=join_tags(n.tags),
                    fields=n.fields,
                    guid=n.guid,
                    flags=n.flags
                    # media_references=n.media_references or n.get_media_references()
               ) for n in self.notes]


@dataclass
class Notes(YamlRepr):
    note_groupings: List[NoteGrouping]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(note_groupings=list(map(NoteGrouping.from_dict, data.get(NOTE_GROUPINGS))))

    @classmethod
    def from_list_of_notes(cls, notes: List[Note]):
        return cls(note_groupings=[NoteGrouping(note_model=None, tags=None, notes=notes)])  # TODO: Check grouping here

    def encode(self) -> dict:
        data_dict = {NOTE_GROUPINGS: [note_grouping.encode() for note_grouping in self.note_groupings]}
        return data_dict

    def get_all_known_note_model_names(self):
        return {nms for group in self.note_groupings for nms in group.get_all_known_note_model_names()}

    def get_all_media_references(self) -> set:
        all_media = set()
        for note in self.note_groupings:
            for media in note.get_all_media_references():
                all_media = all_media.union(media)
        return all_media

    def get_notes(self):
        return [note for group in self.note_groupings for note in group.get_all_notes_copy()]
