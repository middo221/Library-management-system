"""Seed a plausible small collection: ~40 titles across 8 categories, 1–4 copies each."""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from domains.catalog.models import Author, Book, BookCopy, Category

CATEGORIES = [
    ("Fiction", "Novels and short stories."),
    ("Science", "Physics, biology, chemistry and the history of ideas."),
    ("History", "Accounts of the past and the arguments about them."),
    ("Philosophy", "Ethics, metaphysics, logic."),
    ("Poetry", "Verse, collected and single-author."),
    ("Technology", "Computing, engineering and craft."),
    ("Biography", "Lives, told by others and by themselves."),
    ("Reference", "Dictionaries, atlases and handbooks."),
]

# (title, author, category, year, publisher, pages, dewey prefix)
BOOKS = [
    ("Ulysses", "James Joyce", "Fiction", 1922, "Shakespeare and Company", 730, "823.912"),
    ("Mrs Dalloway", "Virginia Woolf", "Fiction", 1925, "Hogarth Press", 194, "823.912"),
    ("To the Lighthouse", "Virginia Woolf", "Fiction", 1927, "Hogarth Press", 209, "823.912"),
    ("Things Fall Apart", "Chinua Achebe", "Fiction", 1958, "Heinemann", 209, "823.914"),
    ("Beloved", "Toni Morrison", "Fiction", 1987, "Alfred A. Knopf", 324, "813.54"),
    ("The Left Hand of Darkness", "Ursula K. Le Guin", "Fiction", 1969, "Ace Books", 304, "813.54"),
    (
        "A Wizard of Earthsea",
        "Ursula K. Le Guin",
        "Fiction",
        1968,
        "Parnassus Press",
        183,
        "813.54",
    ),
    ("Invisible Cities", "Italo Calvino", "Fiction", 1972, "Einaudi", 165, "853.914"),
    (
        "If on a Winter's Night a Traveller",
        "Italo Calvino",
        "Fiction",
        1979,
        "Einaudi",
        260,
        "853.914",
    ),
    (
        "The Remains of the Day",
        "Kazuo Ishiguro",
        "Fiction",
        1989,
        "Faber and Faber",
        258,
        "823.914",
    ),
    ("Never Let Me Go", "Kazuo Ishiguro", "Fiction", 2005, "Faber and Faber", 288, "823.914"),
    ("Wolf Hall", "Hilary Mantel", "Fiction", 2009, "Fourth Estate", 653, "823.914"),
    ("A Brief History of Time", "Stephen Hawking", "Science", 1988, "Bantam Books", 212, "523.1"),
    (
        "The Selfish Gene",
        "Richard Dawkins",
        "Science",
        1976,
        "Oxford University Press",
        224,
        "576.5",
    ),
    ("Silent Spring", "Rachel Carson", "Science", 1962, "Houghton Mifflin", 368, "363.738"),
    ("The Origin of Species", "Charles Darwin", "Science", 1859, "John Murray", 502, "576.82"),
    ("Cosmos", "Carl Sagan", "Science", 1980, "Random House", 365, "520"),
    (
        "The Structure of Scientific Revolutions",
        "Thomas Kuhn",
        "Science",
        1962,
        "University of Chicago Press",
        264,
        "501",
    ),
    ("SPQR", "Mary Beard", "History", 2015, "Profile Books", 606, "937"),
    ("The Guns of August", "Barbara Tuchman", "History", 1962, "Macmillan", 511, "940.421"),
    ("Sapiens", "Yuval Noah Harari", "History", 2011, "Harvill Secker", 443, "909"),
    (
        "The Making of the English Working Class",
        "E. P. Thompson",
        "History",
        1963,
        "Victor Gollancz",
        848,
        "305.562",
    ),
    ("Citizens", "Simon Schama", "History", 1989, "Alfred A. Knopf", 948, "944.04"),
    ("Meditations", "Marcus Aurelius", "Philosophy", 180, "Penguin Classics", 254, "188"),
    ("The Republic", "Plato", "Philosophy", -380, "Penguin Classics", 416, "184"),
    (
        "Philosophical Investigations",
        "Ludwig Wittgenstein",
        "Philosophy",
        1953,
        "Blackwell",
        250,
        "192",
    ),
    (
        "A Theory of Justice",
        "John Rawls",
        "Philosophy",
        1971,
        "Harvard University Press",
        607,
        "320.011",
    ),
    ("The Second Sex", "Simone de Beauvoir", "Philosophy", 1949, "Gallimard", 746, "305.42"),
    ("Ariel", "Sylvia Plath", "Poetry", 1965, "Faber and Faber", 86, "811.54"),
    ("North", "Seamus Heaney", "Poetry", 1975, "Faber and Faber", 73, "821.914"),
    (
        "The Waste Land and Other Poems",
        "T. S. Eliot",
        "Poetry",
        1922,
        "Faber and Faber",
        88,
        "821.912",
    ),
    ("Selected Poems", "Emily Dickinson", "Poetry", 1890, "Roberts Brothers", 210, "811.4"),
    (
        "Structure and Interpretation of Computer Programs",
        "Harold Abelson",
        "Technology",
        1985,
        "MIT Press",
        657,
        "005.133",
    ),
    ("The Pragmatic Programmer", "Andrew Hunt", "Technology", 1999, "Addison-Wesley", 352, "005.1"),
    ("Design Patterns", "Erich Gamma", "Technology", 1994, "Addison-Wesley", 395, "005.12"),
    (
        "The Mythical Man-Month",
        "Frederick Brooks",
        "Technology",
        1975,
        "Addison-Wesley",
        322,
        "005.1",
    ),
    ("Code", "Charles Petzold", "Technology", 1999, "Microsoft Press", 393, "004"),
    (
        "The Diary of a Young Girl",
        "Anne Frank",
        "Biography",
        1947,
        "Contact Publishing",
        283,
        "940.5318",
    ),
    ("Long Walk to Freedom", "Nelson Mandela", "Biography", 1994, "Little, Brown", 656, "968.065"),
    ("The Elements of Style", "William Strunk Jr.", "Reference", 1918, "Harcourt", 105, "808.042"),
    ("Roget's Thesaurus", "Peter Mark Roget", "Reference", 1852, "Longman", 1300, "423"),
]


def _isbn13(seed: int) -> str:
    """Deterministic, checksum-valid ISBN-13 so seeded data passes the same validator as input."""
    body = f"978{seed:09d}"
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(body))
    return body + str((10 - total % 10) % 10)


class Command(BaseCommand):
    help = "Seed the catalogue with ~40 titles and their copies."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--seed", type=int, default=20240501)

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        rng = random.Random(options["seed"])

        categories = {}
        for name, description in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            categories[name] = category

        created_books = 0
        created_copies = 0

        for index, (title, author_name, category, year, publisher, pages, dewey) in enumerate(
            BOOKS
        ):
            author, _ = Author.objects.get_or_create(name=author_name)
            isbn = _isbn13(index + 100000)

            book, is_new = Book.objects.get_or_create(
                isbn=isbn,
                defaults={
                    "title": title,
                    "category": categories[category],
                    "published_year": year if year > 0 else None,
                    "publisher": publisher,
                    "page_count": pages,
                    "language": "English",
                    "description": f"{title} by {author_name}.",
                },
            )
            book.authors.add(author)
            created_books += int(is_new)

            surname = author_name.split()[-1][:3].upper()
            call_number = f"{dewey} {surname}"

            for copy_index in range(rng.randint(1, 4)):
                barcode = f"L{index + 1:03d}{copy_index + 1:02d}"
                _, copy_is_new = BookCopy.objects.get_or_create(
                    barcode=barcode,
                    defaults={
                        "book": book,
                        "call_number": call_number,
                        "replacement_cost": rng.choice(["18.00", "24.50", "30.00", "45.00"]),
                    },
                )
                created_copies += int(copy_is_new)

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogue seeded: {created_books} new titles, {created_copies} new copies."
            )
        )
