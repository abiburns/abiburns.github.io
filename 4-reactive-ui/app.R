library(shiny)
library(DBI)
library(RSQLite)

# Define UIS for application
ui <- fluidPage(
  sliderInput("nrows", "Enter the number of rows to display:",
              min = 1,
              max = 1230,
              value = 25),
  # tableOutput("tbl")
  dataTableOutput("tbl")
)

# Define server logic
server <- function(input, output) {
  table <- renderDataTable({
    
    # sqllite
    # Be sure the data file must be in same folder
    sqlite_conn <- dbConnect(RSQLite::SQLite(), dbname ='Dallas Area Rapid Transit.db')
    
    # Create SQL query object
    sqlite_sql="SELECT ArrivalTime, RouteID, RedStation FROM WeekdayArrivalTimes"
    
    conn=sqlite_conn
    str_sql = sqlite_sql
    
    on.exit(dbDisconnect(conn), add = TRUE)
    table_df = dbGetQuery(conn, paste0(str_sql, " LIMIT ", input$nrows, ";"))
  }, escape = FALSE)
  
  output$tbl <- table
  
  
}

# Run the application 
shinyApp(ui = ui, server = server)