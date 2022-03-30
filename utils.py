import datetime
from random import randrange, randint

from config import CITIES_AND_FLIGHT_TIME as SFT


async def dispatcher(city_from, city_to, chosen_date):
    flights = []
    number_of_flights = 5

    flight_time = SFT[city_from].get(city_to) if SFT[city_from].get(city_to) else SFT[city_to].get(city_from)

    for _ in range(number_of_flights):
        departure_time = datetime.datetime.strptime(chosen_date, '%d-%m-%Y') + datetime.timedelta(hours=randint(0, 72))
        departure_time = departure_time.replace(minute=randrange(0, 60, 10))
        departure_time_str = departure_time.strftime('%H:%M %d-%m-%Y')

        arrival_time = departure_time + datetime.timedelta(hours=flight_time)
        arrival_time_str = arrival_time.strftime('%H:%M %d-%m-%Y')

        flights.append((departure_time_str, arrival_time_str, flight_time))

    flights = sorted(flights, key=lambda d: datetime.datetime.strptime(d[0], '%H:%M %d-%m-%Y'))

    return flights
