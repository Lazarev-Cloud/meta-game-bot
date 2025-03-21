import logging
import sqlite3
import random
from datetime import datetime, timedelta
from db.utils import DB_PATH

logger = logging.getLogger(__name__)

# Ideology scales: from -5 (complete reformist) to +5 (preservation of old order)
IDEOLOGY_SCALE = {
    -5: "Strongly Reformist",
    -4: "Reformist",
    -3: "Moderately Reformist",
    -2: "Slightly Reformist",
    -1: "Mildly Reformist",
    0: "Neutral/Pragmatic",
    1: "Mildly Conservative",
    2: "Slightly Conservative",
    3: "Moderately Conservative",
    4: "Conservative",
    5: "Strongly Conservative"
}

# Politicians definitions based on game rules
# Each politician has:
# - A role and description
# - An ideological position (-5 to +5)
# - Associated district and influence in it
# - Special abilities/bonuses
LOCAL_POLITICIANS = {
    "nemanja_kovacevic": {
        "name": "Nemanja Kovačević",
        "role": "Head of Novi Sad City Administration",
        "description": "Loyal to the Milošević regime, opponent of radical changes, controls city administrative resources",
        "ideology": 5,  # +5 = Preservation of the old order
        "district": "stari_grad",
        "district_influence": 6,  # +6 Control Points in district
        "bonuses": {
            "regime_support": 5,  # +5 CP for regime support actions
            "reforms_penalty": -3  # -3 CP for reform actions
        }
    },
    "miroslav_vasilevic": {
        "name": "Miroslav Vasiljević",
        "role": "Deputy Head of Administration",
        "description": "Can slow down reforms, but helps with bureaucracy",
        "ideology": 3,  # +3 = Conservative
        "district": "stari_grad",
        "district_influence": 4,
        "bonuses": {
            "bureaucracy_help": 3,  # +3 CP when dealing with bureaucracy
            "reforms_penalty": -2  # -2 CP for reform actions
        }
    },
    "dragan_jovic": {
        "name": "Professor Dragan Jović",
        "role": "Rector of Novi Sad University",
        "description": "Intellectual, supporter of democratization and European integration, influential among students and intelligentsia",
        "ideology": -5,  # -5 = Reforms
        "district": "liman",
        "district_influence": 7,
        "bonuses": {
            "reforms_support": 5,  # +5 CP for reform actions
            "regime_penalty": -3  # -3 CP for regime support actions
        }
    },
    "zoran_novakovic": {
        "name": "Zoran \"Zoki\" Novakovic",
        "role": "Leader of local criminal group",
        "description": "Controls part of the shadow economy, has connections with law enforcement",
        "ideology": 3,  # +3 = Conservative
        "district": "salajka",
        "district_influence": 5,
        "bonuses": {
            "force_resources": 3,  # +3 Force resources when allied
            "attack_penalty": -3  # -3 CP for attack actions against his group
        }
    },
    "jovan_miric": {
        "name": "Jovan Mirić",
        "role": "Diplomat working with international organizations",
        "description": "Provides connection with foreign partners, navigates between regime interests and the West",
        "ideology": 2,  # +2 = Slightly conservative
        "district": "petrovaradin",
        "district_influence": 4,
        "bonuses": {
            "foreign_support": 4,  # +4 CP for foreign support actions
            "external_resources": 2  # Can attract external resources
        }
    },
    "branko_petrovic": {
        "name": "Colonel Branko Petrović",
        "role": "Commander of the Novi Sad military garrison",
        "description": "Military with traditionalist views, loyal to the regime and ready for decisive measures",
        "ideology": 4,  # +4 = Conservative
        "district": "novo_naselje",
        "district_influence": 6,
        "bonuses": {
            "defense_actions": 5,  # +5 CP for defense actions
            "protest_penalty": -5  # -5 CP against protest actions
        }
    },
    "goran_radic": {
        "name": "Goran Radić",
        "role": "Leader of the Machine Builders Union",
        "description": "Represents workers' interests, criticizes economic policy but takes a moderate position",
        "ideology": -2,  # -2 = Reformist
        "district": "podbara",
        "district_influence": 4,
        "bonuses": {
            "alliance_resources": 3,  # +3 Resources when allied
            "conflict_resources": -3  # -3 Resources when in conflict
        }
    },
    "maria_kovac": {
        "name": "Maria Kovač",
        "role": "Leader of the student movement 'Otpor'",
        "description": "Charismatic leader of youth protest, demands democratization and change of power",
        "ideology": -4,  # -4 = Reformist
        "district": "liman",
        "district_influence": 5,
        "bonuses": {
            "mass_actions": 5,  # +5 CP for mass actions
            "force_control_penalty": -3  # -3 CP against forceful control
        }
    },
    "bishop_irinej": {
        "name": "Bishop Irinej",
        "role": "Head of the Orthodox Diocese in Novi Sad",
        "description": "Supports traditional values but advocates for peace and harmony, against violence",
        "ideology": 1,  # +1 = Conservative with moderate influence
        "district": "petrovaradin",
        "district_influence": 5,
        "bonuses": {
            "public_opinion": 4,  # Ability to influence public opinion
            "violence_penalty": -4  # -4 CP against violent actions
        }
    }
}

# International politicians with their influence mechanics
INTERNATIONAL_POLITICIANS = {
    "bill_clinton": {
        "name": "Bill Clinton",
        "country": "USA",
        "ideology": -5,  # Strongly reformist
        "influence_level": "high",
        "activity": 80,  # 80% chance of intervention
        "actions": [
            {
                "name": "Economic Sanctions",
                "effect": {
                    "type": "district_penalty",
                    "target_ideology": "conservative",
                    "control_change": -8
                },
                "description": "USA imposes sanctions against the regime, districts under conservative control get -8 CP"
            },
            {
                "name": "Support Opposition",
                "effect": {
                    "type": "district_bonus",
                    "target_ideology": "reformist",
                    "control_change": 6
                },
                "description": "USA provides support for reformist forces, districts with reformist control get +6 CP"
            }
        ]
    },
    "tony_blair": {
        "name": "Tony Blair",
        "country": "United Kingdom",
        "ideology": -4,  # Reformist
        "influence_level": "medium",
        "activity": 60,
        "actions": [
            {
                "name": "Economic Reform Pressure",
                "effect": {
                    "type": "economic_districts_penalty",
                    "target_ideology": "conservative",
                    "control_change": -5
                },
                "description": "UK pushes for economic reforms, economic districts under conservative control get -5 CP"
            }
        ]
    },
    "jacques_chirac": {
        "name": "Jacques Chirac",
        "country": "France",
        "ideology": -3,  # Moderately reformist
        "influence_level": "medium",
        "activity": 50,
        "actions": [
            {
                "name": "Diplomatic Support",
                "effect": {
                    "type": "diplomatic_boost",
                    "target_ideology": "any",
                    "resource_gain": "influence"
                },
                "description": "France provides diplomatic channels, all players can gain +2 Influence resource"
            }
        ]
    },
    "joschka_fischer": {
        "name": "Joschka Fischer",
        "country": "Germany",
        "ideology": -2,  # Slightly reformist
        "influence_level": "medium",
        "activity": 40,
        "actions": [
            {
                "name": "Support for Democratic Activists",
                "effect": {
                    "type": "district_bonus",
                    "target_ideology": "reformist",
                    "control_change": 4
                },
                "description": "Germany supports democratic activists, reformist districts get +4 CP"
            }
        ]
    },
    "javier_solana": {
        "name": "Javier Solana",
        "country": "NATO",
        "ideology": -3,  # Moderately reformist
        "influence_level": "high",
        "activity": 70,
        "actions": [
            {
                "name": "Military Pressure",
                "effect": {
                    "type": "military_district_penalty",
                    "district": "novo_naselje",
                    "control_change": -7
                },
                "description": "NATO threatens military action, military district (Novo Naselje) gets -7 CP for conservatives"
            }
        ]
    },
    "zhirinovsky": {
        "name": "Vladimir Zhirinovsky",
        "country": "Russia",
        "ideology": 4,  # Conservative
        "influence_level": "medium",
        "activity": 50,
        "actions": [
            {
                "name": "Support for Destabilization",
                "effect": {
                    "type": "chaos_bonus",
                    "target": "protest_districts",
                    "control_change": 5
                },
                "description": "Russia supports destabilization, districts with protests get +5 CP of chaos"
            }
        ]
    },
    "primakov": {
        "name": "Yevgeny Primakov",
        "country": "Russia",
        "ideology": 2,  # Slightly conservative
        "influence_level": "high",
        "activity": 60,
        "actions": [
            {
                "name": "Diplomatic Support for Regime",
                "effect": {
                    "type": "sanction_resistance",
                    "target_ideology": "conservative",
                    "control_penalty_reduction": 4
                },
                "description": "Russia provides diplomatic support to resist sanctions, reducing penalty by 4 CP"
            }
        ]
    },
    "milosevic": {
        "name": "Slobodan Milošević",
        "country": "Yugoslavia",
        "ideology": 5,  # Strongly conservative
        "influence_level": "very_high",
        "activity": 95,
        "actions": [
            {
                "name": "Government Crackdown",
                "effect": {
                    "type": "district_penalty",
                    "target_ideology": "reformist",
                    "control_change": -10
                },
                "description": "Milošević orders harsh measures against opposition, reformist districts lose 10 CP"
            },
            {
                "name": "Resource Redistribution",
                "effect": {
                    "type": "resource_distortion",
                    "target_ideology": "reformist",
                    "resource_penalty": "influence"
                },
                "description": "Milošević uses state apparatus to suppress opposition, reformists lose 2 Influence resource"
            },
            {
                "name": "Military Support",
                "effect": {
                    "type": "military_district_bonus",
                    "district": "novo_naselje",
                    "control_change": 8
                },
                "description": "Milošević strengthens military presence, Novo Naselje district gets +8 CP for regime supporters"
            }
        ]
    },
    "havel": {
        "name": "Václav Havel",
        "country": "Czech Republic",
        "ideology": -5,  # Strongly reformist
        "influence_level": "medium",
        "activity": 40,
        "actions": [
            {
                "name": "NGO Support",
                "effect": {
                    "type": "resource_boost",
                    "target_ideology": "reformist",
                    "resource_gain": "information"
                },
                "description": "Havel's support for NGOs gives reformist players +2 Information resource"
            }
        ]
    },
    "albright": {
        "name": "Madeleine Albright",
        "country": "USA",
        "ideology": -4,  # Reformist
        "influence_level": "high",
        "activity": 70,
        "actions": [
            {
                "name": "Tough Sanctions",
                "effect": {
                    "type": "economic_districts_penalty",
                    "target_ideology": "conservative",
                    "control_change": -7
                },
                "description": "Albright pushes for tougher sanctions, economic districts under conservative control get -7 CP"
            }
        ]
    }
}

def get_politician_info(politician_id):
    """Get detailed information about a politician."""
    try:
        # First, check local politicians
        if politician_id in LOCAL_POLITICIANS:
            return LOCAL_POLITICIANS[politician_id]
        
        # Then check international politicians
        if politician_id in INTERNATIONAL_POLITICIANS:
            return INTERNATIONAL_POLITICIANS[politician_id]
        
        # If not found in memory, check the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM politicians WHERE politician_id = ?", (politician_id,))
        politician_data = cursor.fetchone()
        conn.close()
        
        if politician_data:
            # Format data from database row
            return {
                "id": politician_data[0],
                "name": politician_data[1],
                "role": politician_data[2],
                "description": politician_data[3],
                "ideology": politician_data[4],
                "district": politician_data[5],
                "district_influence": politician_data[6],
                "is_international": politician_data[7] == 1
            }
        
        return None
    except Exception as e:
        logger.error(f"Error getting politician info: {e}")
        return None

def get_random_international_politicians(min_count=1, max_count=3):
    """Get a random selection of international politicians for a game cycle."""
    try:
        politician_ids = list(INTERNATIONAL_POLITICIANS.keys())
        active_politicians = []
        
        # Determine how many politicians will be active
        count = random.randint(min_count, max_count)
        
        # Select random politicians based on their activity probability
        for politician_id in politician_ids:
            politician = INTERNATIONAL_POLITICIANS[politician_id]
            if random.randint(1, 100) <= politician["activity"]:
                active_politicians.append(politician_id)
            
            # If we have enough active politicians, stop
            if len(active_politicians) >= count:
                break
                
        # If we don't have enough, just pick randomly to ensure minimum count
        if len(active_politicians) < min_count:
            remaining_ids = [pid for pid in politician_ids if pid not in active_politicians]
            additional_needed = min_count - len(active_politicians)
            active_politicians.extend(random.sample(remaining_ids, min(additional_needed, len(remaining_ids))))
        
        return active_politicians
    except Exception as e:
        logger.error(f"Error selecting international politicians: {e}")
        return []

def process_international_politician_action(politician_id):
    """Process an action by an international politician."""
    try:
        if politician_id not in INTERNATIONAL_POLITICIANS:
            logger.error(f"Unknown international politician: {politician_id}")
            return False
            
        politician = INTERNATIONAL_POLITICIANS[politician_id]
        
        # Select a random action from the politician's available actions
        if politician["actions"]:
            action = random.choice(politician["actions"])
            logger.info(f"International politician {politician['name']} performing action: {action['name']}")
            
            # Apply the action effects (in a real implementation, this would affect game state)
            # This is a placeholder for actual game mechanics implementation
            apply_international_action_effects(politician, action)
            
            # Create a news item about this action
            from db.queries import add_news
            add_news(
                title=f"{politician['name']} ({politician['country']}) takes action!",
                content=action["description"],
                is_public=True
            )
            
            return True
        else:
            logger.warning(f"Politician {politician_id} has no defined actions")
            return False
    except Exception as e:
        logger.error(f"Error processing international politician action: {e}")
        return False

def apply_international_action_effects(politician, action):
    """Apply the effects of an international politician's action."""
    try:
        effect = action["effect"]
        effect_type = effect["type"]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if effect_type == "district_penalty" or effect_type == "district_bonus":
            # Apply control point changes to districts based on ideology
            target_ideology = effect["target_ideology"]
            control_change = effect["control_change"]
            
            # In a real implementation, this would identify districts controlled by the target ideology
            # and apply the control point changes
            logger.info(f"Applied {effect_type} of {control_change} CP to {target_ideology} districts")
            
        elif effect_type == "economic_districts_penalty":
            # Apply penalties to economic districts (like Novo Naselje, Podbara)
            economic_districts = ["novo_naselje", "podbara"]
            target_ideology = effect["target_ideology"]
            control_change = effect["control_change"]
            
            # In a real implementation, this would identify economic districts controlled by the target ideology
            # and apply the control point changes
            logger.info(f"Applied economic penalty of {control_change} CP to {target_ideology} economic districts")
            
        elif effect_type == "military_district_penalty":
            # Apply penalties specifically to military districts
            district = effect["district"]
            # Update district reference if needed
            if district == "adamovicevo":
                district = "novo_naselje"
            
            control_change = effect["control_change"]
            
            # In a real implementation, this would apply control point changes to the military district
            logger.info(f"Applied military penalty of {control_change} CP to {district} district")
            
        elif effect_type == "resource_boost" or effect_type == "resource_distortion":
            # Add or remove resources from players based on ideology
            target_ideology = effect["target_ideology"]
            resource_type = effect.get("resource_gain") or effect.get("resource_penalty")
            
            # In a real implementation, this would identify players with the target ideology
            # and add or remove resources accordingly
            logger.info(f"Applied {effect_type} of {resource_type} to {target_ideology} players")
            
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error applying international action effects: {e}")
        return False

def calculate_player_politician_ideology_bonus(player_ideology, politician_ideology):
    """
    Calculate the control point bonus a player gets based on ideological alignment with a politician.
    
    Player and politician are compared on the ideology scale (-5 to +5):
    - Difference 0-2: player gets +2 CP per cycle
    - Difference 3+: player gets +5 CP per cycle
    - Difference -3 or less: player loses -5 CP per cycle
    
    Args:
        player_ideology: Integer from -5 to +5
        politician_ideology: Integer from -5 to +5
        
    Returns:
        dict: Bonus information including CP change and message
    """
    ideology_difference = player_ideology - politician_ideology
    
    # The difference is the absolute value
    difference = abs(ideology_difference)
    
    if 0 <= difference <= 2:
        return {
            "control_change": 2,
            "message": "Small ideological difference (+2 CP)"
        }
    elif difference >= 3:
        return {
            "control_change": 5,
            "message": "Major ideological alignment (+5 CP)"
        }
    else:
        return {
            "control_change": -5,
            "message": "Ideological opposition (-5 CP)"
        } 