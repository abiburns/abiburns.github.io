library(shiny)
library(DBI)
library(RSQLite)
library(rsconnect)

# Define UIS for application
ui <- fluidPage(
  sliderInput("nrows", "Enter the number of rows to display:",
              min = 1,
              max = 1230,
              value = 100),
  # tableOutput("tbl")
  dataTableOutput("tbl"),
  # textInput
  textInput("route", "Choose route:", ""),
  textInput("station", "Choose station:", "")
)

# Define server logic
server <- function(input, output) {
  table <- renderDataTable({
    
    # sqllite
    # Be sure the data file must be in same folder
    sqlite_conn <- dbConnect(RSQLite::SQLite(), dbname ='Dallas Area Rapid Transit.db')
    conn=sqlite_conn
    
    on.exit(dbDisconnect(conn), add = TRUE)
    query <- paste0("SELECT ArrivalTime, RouteID, RedStation FROM WeekdayArrivalTimes WHERE RouteID LIKE '%", input$route, "%' AND RedStation LIKE '%", input$station, "%'")
    table_df = dbGetQuery(conn, paste0(query, " LIMIT ", input$nrows, ";"))
  }, escape = FALSE)
  
  output$tbl <- table
  
  
}

# Run the application 
shinyApp(ui = ui, server = server)

#Deploy
#rsconnect::setAccountInfo(name='abiburns', token='7C58F1794F423FA952B50D2EE0747BE3', secret='LWMFuxG0fo2OJZiy/xbU3RE+3XgePm5psYMhOo5u')