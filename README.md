# LatigoScraper

Framework de webscraping para conectarse con los portales de bancos mas importantes de México y obtener las transacciones de un cuentahabiente.

Los bancos soportados hasta el momento:
* HSBC
* Banregio (En desarrollo)

## Uso
```python
import latigoscraper
hsbc = latigoscraper.HSBC("juan_perez", "********")
hsbc.login_to_account_home()
hsbc.get_transactions()
```

_Nota: Está en modo experimental y fue creado en el Startupbootcamp FinTech Hackathon Vol.02 en la Ciudad de México_