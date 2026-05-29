"""
crm/cirkanime_seed.py — One-time seed script with Nic Idées / Cirkanime data.

Run: python -m crm.cirkanime_seed
"""

from crm.db import init_db, add_organisation, add_event, log_contact


def seed():
    """Populate the CRM with Nic Idées' territory data."""
    init_db()

    orgs = {}

    # -----------------------------------------------------------------------
    # Organisations
    # -----------------------------------------------------------------------

    orgs["repentigny"] = add_organisation(
        name="Ville de Repentigny", org_type="Municipalite",
        city="Repentigny", contact_person="Service des loisirs",
        activity_tags="cirque,animation,evenements municipaux,famille",
        notes="Très actif: cinéma plein air, fête nationale, Halloween, Noël, camps de jour.",
        potential_value=6000,
    )
    orgs["montreal"] = add_organisation(
        name="Ville de Montréal", org_type="Municipalite",
        city="Montréal", contact_person="Service des loisirs",
        activity_tags="cirque,animation,fete,parascolaire,famille",
        notes="Multiples arrondissements. Fêtes de quartier, cinéma plein air, marchés publics.",
        potential_value=8000,
    )
    orgs["laval"] = add_organisation(
        name="Ville de Laval", org_type="Municipalite",
        city="Laval", contact_person="Service des loisirs",
        activity_tags="cirque,animation,fete,famille,camps",
        notes="Laval en blanc, fête nationale, Noël, camps de jour, festivals de quartier.",
        potential_value=7000,
    )
    orgs["sainte_therese"] = add_organisation(
        name="Ville de Sainte-Thérèse", org_type="Municipalite",
        city="Sainte-Thérèse", contact_person="Service des loisirs",
        activity_tags="cirque,animation,illumination,famille",
        notes="Village de Noël, Grande Illumination, cinéma plein air, Halloween.",
        potential_value=4500,
    )
    orgs["joliette"] = add_organisation(
        name="Ville de Joliette", org_type="Municipalite",
        city="Joliette", contact_person="Service des loisirs",
        activity_tags="cirque,animation,festival,famille",
        notes="Festival Bastringue, Fête O'Parc, Spéctacles au parc, Festival du rire.",
        potential_value=5000,
    )
    orgs["mascouche"] = add_organisation(
        name="SODAM / Cirkana — Mascouche", org_type="Organisme",
        city="Mascouche", contact_person="Direction",
        activity_tags="cirque,culture,annuel",
        notes="ÉNORME contact potentiel (Wikipedia). Cirque/culture annuel.",
        potential_value=5000,
    )
    orgs["fete_lac_mem"] = add_organisation(
        name="Festival du Lac-Memphremagog", org_type="Festival",
        city="Magog", contact_person="Comité organisateur",
        activity_tags="festival,spectacle,cirque",
        notes="Festival d'été majeur. Cherche toujours des animateurs.",
        potential_value=4000,
    )
    orgs["camp_repentigny"] = add_organisation(
        name="Camps de jour municipaux — Repentigny", org_type="Camp de jour",
        city="Repentigny", contact_person="Coordination camps",
        activity_tags="camp,cirque,animation,enfants,rotations",
        notes="Rotations / gros jeux. Contacter janvier à mars.",
        potential_value=3000,
    )
    orgs["camp_laval"] = add_organisation(
        name="Camps de jour municipaux — Laval", org_type="Camp de jour",
        city="Laval", contact_person="Coordination camps",
        activity_tags="camp,cirque,animation,enfants,rotations",
        notes="Rotations / gros jeux. Contacter janvier à mars.",
        potential_value=3000,
    )
    orgs["para_montreal"] = add_organisation(
        name="Parascolaire Montréal", org_type="Parascolaire",
        city="Montréal", contact_person="Coordination parascolaire",
        activity_tags="parascolaire,cirque,ecole,sessions",
        notes="Sessions pédagogiques. Contacter août à décembre.",
        potential_value=3500,
    )
    orgs["para_laval"] = add_organisation(
        name="Parascolaire Laval", org_type="Parascolaire",
        city="Laval", contact_person="Coordination parascolaire",
        activity_tags="parascolaire,cirque,ecole,sessions",
        notes="Sessions pédagogiques. Contacter août à décembre.",
        potential_value=3000,
    )

    # -----------------------------------------------------------------------
    # Events — with numeric contact_month_start / contact_month_end
    # -----------------------------------------------------------------------

    # REPENTIGNY
    add_event(
        event_name="Cinéma en plein air — Repentigny",
        city="Repentigny", event_type="Famille",
        period="Juillet–août", best_contact="Avril → juin",
        contact_month_start=4, contact_month_end=6,
        org_id=orgs["repentigny"],
        notes="Pré-animation familiale.",
    )
    add_event(
        event_name="Fête nationale — Repentigny",
        city="Repentigny", event_type="Fête de quartier",
        period="Juin", best_contact="Janvier → avril",
        contact_month_start=1, contact_month_end=4,
        org_id=orgs["repentigny"],
        notes="Animation jeunesse / défis participatifs.",
    )
    add_event(
        event_name="Activités estivales des parcs — Repentigny",
        city="Repentigny", event_type="Famille",
        period="Été", best_contact="Février → mai",
        contact_month_start=2, contact_month_end=5,
        org_id=orgs["repentigny"],
        notes="Kiosque cirque / animation libre.",
    )
    add_event(
        event_name="Halloween municipal — Repentigny",
        city="Repentigny", event_type="Famille",
        period="Octobre", best_contact="Juin → août",
        contact_month_start=6, contact_month_end=8,
        org_id=orgs["repentigny"],
        notes="Animation clownesque / déambulatoire.",
    )
    add_event(
        event_name="Relâche scolaire — Repentigny",
        city="Repentigny", event_type="Jeunesse",
        period="Mars", best_contact="Novembre → janvier",
        contact_month_start=11, contact_month_end=1,
        org_id=orgs["repentigny"],
        notes="Ateliers jeunesse.",
    )
    add_event(
        event_name="Noël / marché de Noël — Repentigny",
        city="Repentigny", event_type="Famille",
        period="Décembre", best_contact="Août → octobre",
        contact_month_start=8, contact_month_end=10,
        org_id=orgs["repentigny"],
        notes="Animation hivernale / LED.",
    )
    add_event(
        event_name="Mélo Festival — Repentigny",
        city="Repentigny", event_type="Festival",
        period="Juin", best_contact="Janvier → mars",
        contact_month_start=1, contact_month_end=3,
        org_id=orgs["repentigny"],
        notes="Animation ambiance / site festival.",
    )
    add_event(
        event_name="Fête au Petit Village — Repentigny",
        city="Repentigny", event_type="Patrimoine/famille",
        period="Septembre", best_contact="Avril → juin",
        contact_month_start=4, contact_month_end=6,
        org_id=orgs["repentigny"],
    )
    add_event(
        event_name="Marchés publics — Repentigny",
        city="Repentigny", event_type="Famille",
        period="Été–automne", best_contact="Printemps",
        contact_month_start=3, contact_month_end=5,
        org_id=orgs["repentigny"],
        notes="Animation ambulante.",
    )
    add_event(
        event_name="Journées familiales municipales — Repentigny",
        city="Repentigny", event_type="Cirque participatif",
        period="Toute l'année", best_contact="3 à 6 mois avant",
        contact_month_start=1, contact_month_end=12,
        org_id=orgs["repentigny"],
    )
    add_event(
        event_name="Camps de jour municipaux — Repentigny",
        city="Repentigny", event_type="Camp",
        period="Été", best_contact="Janvier → mars",
        contact_month_start=1, contact_month_end=3,
        org_id=orgs["camp_repentigny"],
        notes="Rotations / gros jeux.",
    )
    add_event(
        event_name="Parascolaire Repentigny",
        city="Repentigny", event_type="Parascolaire",
        period="Automne / hiver", best_contact="Août → octobre",
        contact_month_start=8, contact_month_end=10,
        org_id=orgs["repentigny"],
        notes="Sessions pédagogiques.",
    )

    # MONTRÉAL
    add_event(
        event_name="Fêtes de quartier — Montréal",
        city="Montréal", event_type="Famille / kiosque cirque",
        period="Été", best_contact="Février → mai",
        contact_month_start=2, contact_month_end=5,
        org_id=orgs["montreal"],
        notes="Multiples arrondissements.",
    )
    add_event(
        event_name="Cinéma plein air — Montréal",
        city="Montréal", event_type="Pré-animation",
        period="Été", best_contact="Avril → juin",
        contact_month_start=4, contact_month_end=6,
        org_id=orgs["montreal"],
    )
    add_event(
        event_name="Journées familiales — Montréal",
        city="Montréal", event_type="Ateliers participatifs",
        period="Toute l'année", best_contact="3–6 mois avant",
        contact_month_start=1, contact_month_end=12,
        org_id=orgs["montreal"],
    )
    add_event(
        event_name="Fête nationale — Montréal",
        city="Montréal", event_type="Animation extérieure",
        period="Juin", best_contact="Janvier → avril",
        contact_month_start=1, contact_month_end=4,
        org_id=orgs["montreal"],
    )
    add_event(
        event_name="Marchés publics — Montréal",
        city="Montréal", event_type="Déambulatoire / ambiance",
        period="Été–automne", best_contact="Avril → juin",
        contact_month_start=4, contact_month_end=6,
        org_id=orgs["montreal"],
    )
    add_event(
        event_name="Festivals de quartier — Montréal",
        city="Montréal", event_type="Animation ambulante",
        period="Été", best_contact="Janvier → mai",
        contact_month_start=1, contact_month_end=5,
        org_id=orgs["montreal"],
    )
    add_event(
        event_name="Parascolaire — Montréal",
        city="Montréal", event_type="Sessions pédagogiques",
        period="Automne / hiver", best_contact="Août → décembre",
        contact_month_start=8, contact_month_end=12,
        org_id=orgs["para_montreal"],
    )
    add_event(
        event_name="Halloween — Montréal",
        city="Montréal", event_type="Personnages / animation",
        period="Octobre", best_contact="Juin → août",
        contact_month_start=6, contact_month_end=8,
        org_id=orgs["montreal"],
    )
    add_event(
        event_name="Noël / marchés de Noël — Montréal",
        city="Montréal", event_type="LED / personnages hivernaux",
        period="Novembre–décembre", best_contact="Août → octobre",
        contact_month_start=8, contact_month_end=10,
        org_id=orgs["montreal"],
    )

    # LAVAL
    add_event(
        event_name="Laval en blanc",
        city="Laval", event_type="Animation hivernale / LED",
        period="Janvier–février", best_contact="Septembre → novembre",
        contact_month_start=9, contact_month_end=11,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Relâche scolaire — Laval",
        city="Laval", event_type="Ateliers découverte",
        period="Mars", best_contact="Novembre → janvier",
        contact_month_start=11, contact_month_end=1,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Camps de jour municipaux — Laval",
        city="Laval", event_type="Camp",
        period="Été", best_contact="Janvier → mars",
        contact_month_start=1, contact_month_end=3,
        org_id=orgs["camp_laval"],
        notes="Rotations / gros jeux.",
    )
    add_event(
        event_name="Fête nationale — Laval",
        city="Laval", event_type="Animation familiale",
        period="Juin", best_contact="Janvier → avril",
        contact_month_start=1, contact_month_end=4,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Activités dans les parcs — Laval",
        city="Laval", event_type="Stations cirque",
        period="Été", best_contact="Février → mai",
        contact_month_start=2, contact_month_end=5,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Festivals de quartier — Laval",
        city="Laval", event_type="Déambulatoire / ambiance",
        period="Été", best_contact="Février → mai",
        contact_month_start=2, contact_month_end=5,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Halloween municipal — Laval",
        city="Laval", event_type="Personnages / ambiance",
        period="Octobre", best_contact="Juin → août",
        contact_month_start=6, contact_month_end=8,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Noël / marchés de Noël — Laval",
        city="Laval", event_type="Jonglerie LED / personnages",
        period="Novembre–décembre", best_contact="Août → octobre",
        contact_month_start=8, contact_month_end=10,
        org_id=orgs["laval"],
    )
    add_event(
        event_name="Parascolaire — Laval",
        city="Laval", event_type="Sessions pédagogiques",
        period="Automne / hiver", best_contact="Août → décembre",
        contact_month_start=8, contact_month_end=12,
        org_id=orgs["para_laval"],
    )

    # SAINTE-THÉRÈSE
    add_event(
        event_name="Village de Noël — Sainte-Thérèse",
        city="Sainte-Thérèse", event_type="Animation lumineuse / LED",
        period="Fin novembre–décembre", best_contact="Août → octobre",
        contact_month_start=8, contact_month_end=10,
        org_id=orgs["sainte_therese"],
    )
    add_event(
        event_name="Grande Illumination du Village — Sainte-Thérèse",
        city="Sainte-Thérèse", event_type="Déambulatoire / animation festive",
        period="Novembre", best_contact="Septembre",
        contact_month_start=9, contact_month_end=9,
        org_id=orgs["sainte_therese"],
    )
    add_event(
        event_name="Cinéma plein air — Sainte-Thérèse",
        city="Sainte-Thérèse", event_type="Pré-animation familiale",
        period="Été", best_contact="Avril → juin",
        contact_month_start=4, contact_month_end=6,
        org_id=orgs["sainte_therese"],
    )
    add_event(
        event_name="Fête nationale — Sainte-Thérèse",
        city="Sainte-Thérèse", event_type="Animation jeunesse / défis",
        period="Juin", best_contact="Janvier → avril",
        contact_month_start=1, contact_month_end=4,
        org_id=orgs["sainte_therese"],
    )
    add_event(
        event_name="Halloween municipal — Sainte-Thérèse",
        city="Sainte-Thérèse", event_type="Personnages loufoques / village",
        period="Octobre", best_contact="Juin → août",
        contact_month_start=6, contact_month_end=8,
        org_id=orgs["sainte_therese"],
    )

    # JOLIETTE
    add_event(
        event_name="Festival Bastringue — Joliette",
        city="Joliette", event_type="Ateliers / animation / déambulatoire",
        period="Juin", best_contact="Janvier → mars",
        contact_month_start=1, contact_month_end=3,
        org_id=orgs["joliette"],
        notes="Festival de cirque — fit naturel.",
    )
    add_event(
        event_name="Fête O'Parc — Joliette",
        city="Joliette", event_type="Animation familiale / stations cirque",
        period="Été / septembre", best_contact="Février → avril",
        contact_month_start=2, contact_month_end=4,
        org_id=orgs["joliette"],
    )
    add_event(
        event_name="Cinéma musical en plein air — Joliette",
        city="Joliette", event_type="Pré-animation familiale",
        period="Juillet–août", best_contact="Avril → juin",
        contact_month_start=4, contact_month_end=6,
        org_id=orgs["joliette"],
    )
    add_event(
        event_name="Festival du rire de Joliette",
        city="Joliette", event_type="Animation ambiance",
        period="Août", best_contact="Mars → juin",
        contact_month_start=3, contact_month_end=6,
        org_id=orgs["joliette"],
    )
    add_event(
        event_name="Marché de Noël de Joliette",
        city="Joliette", event_type="Jonglerie LED / personnages",
        period="Novembre–décembre", best_contact="Août → octobre",
        contact_month_start=8, contact_month_end=10,
        org_id=orgs["joliette"],
    )

    # MASCOUCHE
    add_event(
        event_name="SODAM / Cirkana — Mascouche",
        city="Mascouche", event_type="Cirque/culture",
        period="Annuel", best_contact="Toute l'année",
        contact_month_start=1, contact_month_end=12,
        org_id=orgs["mascouche"],
        notes="ÉNORME contact potentiel (Wikipedia).",
    )

    # -----------------------------------------------------------------------
    # Sample contact logs
    # -----------------------------------------------------------------------
    log_contact(
        org_id=orgs["repentigny"], method="courriel",
        status="Contacté",
        summary="Courriel envoyé au Service des loisirs pour été 2026.",
        follow_up_date="2026-06-10",
    )
    log_contact(
        org_id=orgs["laval"], method="téléphone",
        status="Intéressé",
        summary="Appel avec responsable loisirs. Intéressé pour fête nationale.",
        follow_up_date="2026-06-05",
    )
    log_contact(
        org_id=orgs["joliette"], method="courriel",
        status="À relancer",
        summary="Courriel envoyé pour Festival Bastringue, pas de réponse.",
        follow_up_date="2026-06-01",
    )
    log_contact(
        org_id=orgs["mascouche"], method="messenger",
        status="Bon potentiel futur",
        summary="Contact initial via Wikipedia / réseaux. Fort potentiel annuel.",
        follow_up_date="2026-09-01",
    )

    print(f"[CRM Seed] Done: {len(orgs)} organisations, events seeded for Repentigny / Montréal / Laval / Sainte-Thérèse / Joliette / Mascouche.")


if __name__ == "__main__":
    seed()
