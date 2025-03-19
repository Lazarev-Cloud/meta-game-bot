class Politician:
    """Data model for politicians"""
    def __init__(self, id: int, name: str, role: str, 
                 ideology_score: int, influence: int,
                 description: str, is_international: bool = False):
        self.id = id
        self.name = name
        self.role = role
        self.ideology_score = ideology_score
        self.influence = influence
        self.description = description
        self.is_international = is_international 