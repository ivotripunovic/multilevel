Korisnik vrsi uplatu, ta uplata je u stanju mirovanja dok ne dobijemo od banke poruku da je sve ok, i da je i banka uzela deo, ili da je doslo do greske, pa je uplata nevazeca.

Kada je uplata prosla, najvise tri oca korisnika dobijaju komisiju po procentnoj skali 15, 3, 2

Kada uplata ne prodje onda niko ne dobija nista. 
Svaki korisnik koji ima sredstva od komisije, moze da ih podigne i onda mu se saldo na osnovu toga smanjuje.


Uplate, isplate bankovni fee, isplata na racun komisije, isplata povratak sredstava 
comision uplata, komisija isplata

## VIP Membership
mesecno clanstvo u sistemu


## Tipster
pretplata na redovno pracenje zanimljivih tipstera




```mermaid
erDiagram
    USER ||--o{ SUBSCRIPTION : "has many"
    USER ||--o{ CONTENTSUBSCRIPTION : "has many"
    USER ||--o{ PAYMENTTRANSACTION : "has many"

    SUBSCRIPTIONPLAN ||--o{ SUBSCRIPTION : "is used by"
    SUBSCRIPTIONPLAN {
        int id
        string name
        decimal price
        string interval  
        int duration_in_days
        bool is_active
    }

    SUBSCRIPTION {
        int id
        int user_id
        int plan_id
        datetime start_date
        datetime end_date
        string status     
        bool auto_renew
    }

    PAYMENTSERVICE {
        int id
        string name      
        string type      
    }

    PAYMENTTRANSACTION ||--|| PAYMENTSERVICE : "via"
    SUBSCRIPTION ||--o{ PAYMENTTRANSACTION : "creates"

    PAYMENTTRANSACTION {
        int id
        int user_id
        int subscription_id
        int payment_service_id
        decimal amount
        string currency
        string status        
        string external_id   
        datetime timestamp
    }

    MONTHLYCONTENT ||--o{ CONTENTSUBSCRIPTION : "grants access to"

    MONTHLYCONTENT {
        int id
        string title
        string description
        datetime release_month
        json metadata
    }

    CONTENTSUBSCRIPTION {
        int id
        int user_id
        int content_id
        datetime granted_at
        datetime expires_at
    }
```

