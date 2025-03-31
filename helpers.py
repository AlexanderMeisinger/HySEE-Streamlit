def rename_techs_energy_balance(label):
        prefix_to_remove = [
            "residential ",
            "services ",
            "urban ",
            "rural ",
            "central ",
            "decentral "
        ]
    
        rename_if_contains_dict = {
        "water tanks": "hot water storage", 
        "battery": "battery storage",
        "Battery": "battery storage",
        "Sequestration": "carbon capture",
        "sequestered": "carbon capture"
        }

        rename = {
        # REE
        "Onshore Wind": "onshore wind",
        "Offshore Wind (AC)": "offshore wind",
        "Offshore Wind (DC)": "offshore wind",
        "Offshore Wind (Floating)": "offshore wind",
        "Reservoir & Dam": "hydroelectricity",
        "Run of River": "hydroelectricity",
        "Solar": "solar PV", 
        "solar rooftop": "solar PV",
        "solar-hsat": "solar PV",
        # fossil
        "gas": "gas",
        "oil primary": "oil",
        # biomass 
        "solid biomass": "biomass",
        "unsustainable solid biomass": "biomass",
        "solid biomass CHP": "biomass",
        "solid biomass CHP CC": "biomass",
        # biogas
        "biogas": "biomass", 
        "unsustainable biogas": "biomass",
        "biogas to gas": "biomass",
        # bioliquids
        "unsustainable bioliquids": "biomass",
        # electricity
        "electricity": "residential electricity",
        "industry electricity": "industry electricity",
        "agriculture electricity": "industry electricity",
        "air heat pump": "power-to-heat",
        "ground heat pump": "power-to-heat",
        "resistive heater": "power-to-heat",
        "H2 Electrolysis": "power-to-hydrogen",
        "methanolisation": "power-to-liquid",
        "Methanol steam reforming": "methanol steam reforming",
        "Fischer-Tropsch": "power-to-liquid",
        "methanation": "power-to-methane",
        "Haber-Bosch": "haber-bosch",
        # heat
        "agriculture heat": "heat",
        "heat": "heat",
        "low-temperature heat for industry": "heat",
        # coal 
        "coal for industry": "coal", 
        # biomass
        "solid biomass for industry": "biomass",
        "solid biomass for industry CC": "biomass",
        "biomass boiler": "biomass",
        # methane
        "gas for industry": "methane",
        "gas for industry CC": "methane",
        "gas boiler": "methane",
        "CCGT": "methane",
        "SMR": "steam methane reforming",
        "SMR CC": "steam methane reforming",
        "CHP": "methane",
        "Combined-Cycle Gas": "methane",
        "Open-Cycle Gas": "methane",
        # hydrogen 
        "H2 for industry": "hydrogen",
        "land transport fuel cell": "hydrogen",
        "H2 Fuel Cell": "hydrogen",
        # liquid hydrocarbon
        "kerosene for aviation": "liquid hydrocarbon",
        "naphtha for industry": "liquid hydrocarbon",
        "agriculture machinery oil": "liquid hydrocarbon",
        "shipping oil": "liquid hydrocarbon", 
        "oil refining": "liquid hydrocarbon",
        "land transport oil": "liquid hydrocarbon",
        "shipping methanol": "liquid hydrocarbon",
        "oil boiler": "liquid hydrocarbon",
        # co2
        "DAC": "direct air capture",
        "process emissions CC": "process emissions carbon capture",
        # syngas
        "Sabatier": "methanation",
        # ammonia
        "NH3": "ammonia",
        # battery electric vehicles
        "BEV charger": "battery electric vehicles",
        "V2G": "battery electric vehicles",
        "land transport EV": "battery electric vehicles",
        # others
        "transmission lines": "others",
        "electricity distribution grid": "others",
        "AC": "others", 
        "DC": "others",
        "B2B": "others", 
        # storage
        "Pumped Hydro Storage": "pumped hydro storage",
        "H2 Store": "hydrogen storage",
        # pipeline
        "H2 pipeline": "hydrogen pipeline"
        }

        for ptr in prefix_to_remove:
            while label.startswith(ptr):  # Ensure all occurrences are removed
                label = label[len(ptr):]

        for old,new in rename_if_contains_dict.items():
            if old in label:
                label = new

        for old,new in rename.items():
            if old == label:
                label = new

        return label

def rename_techs_h2_balance(label):    
        rename = {
        "Fischer-Tropsch": "fischer-tropsch",
        "H2 Electrolysis": "H2 electrolysis",
        "H2 Fuel Cell": "H2 fuel cell",
        "SMR": "steam methane reforming",
        "SMR CC": "steam methane reforming carbon capture",
        "Sabatier": "methanation", 
        "Haber-Bosch": "haber-bosch"
        }

        for old,new in rename.items():
            if old == label:
                label = new

        return label

def rename_tech_capacity(label):
        prefix_to_remove = [
            "residential ",
            "services ",
            "urban ",
            "rural ",
            "central ",
            "decentral "
        ]
    
        rename_if_contains_dict = {
        "water tanks": "hot water storage", 
        }
        
        rename = {
            "BEV charger": "battery electric vehicles",
            "EV battery": "battery electric vehicles",
            "V2G": "battery electric vehicles",
            "H2 Store": "hydrogen storage",
            "Onshore Wind": "onshore wind",
            "Offshore Wind (AC)": "offshore wind (AC)",
            "Offshore Wind (DC)": "offshore wind (DC)",
            "Offshore Wind (Floating)": "offshore wind",
            "Pumped Hydro Storage": "pumped hydro storage",
            "Reservoir & Dam": "reservoir & dam",
            "Run of River": "run of river",
            "Solar": "solar PV", 
            "oil primary": "oil",
            "Onshore Wind": "onshore wind",
            "solid biomass CHP": "biomass",
            "solid biomass CHP CC": "biomass",
            "biogas to gas": "biomass",
            "air heat pump": "power-to-heat",
            "ground heat pump": "power-to-heat",
            "resistive heater": "power-to-heat",
            "Fischer-Tropsch": "fischer-tropsch",
            "coal for industry": "coal", 
            "solid biomass for industry": "biomass",
            "solid biomass for industry CC": "biomass",
            "biomass boiler": "biomass",
            "gas for industry": "methane",
            "gas for industry CC": "methane",
            "gas boiler": "methane",
            "CCGT": "methane",
            "SMR": "steam methane reforming",
            "SMR CC": "steam methane reforming",
            "CHP": "methane",
            "Combined-Cycle Gas": "methane",
            "Open-Cycle Gas": "methane",
            "H2 for industry": "hydrogen",
            "land transport fuel cell": "hydrogen",
            "H2 Fuel Cell": "hydrogen",
            "H2 Electrolysis": "hydrogen",
            "kerosene for aviation": "kerosene",
            "naphtha for industry": "naphtha",
            "agriculture machinery oil": "oil",
            "shipping oil": "oil", 
            "oil refining": "oil",
            "land transport oil": "oil",
            "industry methanol": "methanol",
            "shipping methanol": "methanol",
            "oil boiler": "oil",
            "DAC": "direct air capture",
            "process emissions CC": "process emissions",
            "Sabatier": "methanation",
            "transmission lines": "others",
            "electricity distribution grid": "others",
            "AC": "others", 
            "DC": "others",
            "B2B": "others", 
            "H2 pipeline": "hydrogen",
            "Haber-Bosch": "haber-bosch"
            }

        for ptr in prefix_to_remove:
            while label.startswith(ptr):  # Ensure all occurrences are removed
                label = label[len(ptr):]

        for old,new in rename_if_contains_dict.items():
            if old in label:
                label = new

        for old,new in rename.items():
            if old == label:
                label = new

        return label


def prepare_colors(config):
    colors = config["tech_colors"]
    
    return colors
    

